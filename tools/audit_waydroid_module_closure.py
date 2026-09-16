#!/usr/bin/env python3
"""Read-only module-closure gate for the SM-T630 Waydroid kernel."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


RELEASE = "5.4.274-qgki-31225846-abT630XXSBDZE3"
UNUSED_WIFI_MODEL_MODULES = {
    "rmnet_core.ko",
    "rmnet_ctl.ko",
    "rmnet_offload.ko",
    "rmnet_shs.ko",
}
UNUSED_OTHER_PRODUCT_MODULES = {
    # Present in Samsung's broad source/build inventory, but the SM-T630
    # machine driver uses the Cirrus amplifier and must not load this TI
    # amplifier module.  In particular, never use it to satisfy a dependency
    # introduced by a stale non-gtact4pro Samsung product profile.
    "tas256x_dlkm.ko",
}
PERMITTED_UNUSED_MODULES = UNUSED_WIFI_MODEL_MODULES | UNUSED_OTHER_PRODUCT_MODULES


def canonical_name(value: str) -> str:
    return value.replace("-", "_")


def load_abi_module():
    source = Path(__file__).with_name("audit_kernel_module_abi.py")
    spec = importlib.util.spec_from_file_location("t630_kernel_module_abi", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique_by_name(paths: list[Path]) -> dict[str, Path]:
    result = {}
    for path in paths:
        if path.name in result:
            raise ValueError(f"duplicate module basename: {path.name}")
        result[path.name] = path
    return result


def plan_closure(selected: set[str], built: set[str]) -> tuple[set[str], set[str]]:
    eligible_built = built - UNUSED_OTHER_PRODUCT_MODULES
    covered = selected & (eligible_built | {"qca_cld3_wlan.ko"})
    missing = selected - covered
    unexpected = missing - PERMITTED_UNUSED_MODULES
    if unexpected:
        raise ValueError("unresolved modules: " + ",".join(sorted(unexpected)))
    return covered, missing


def parse_loaded(text: str) -> set[str]:
    result = set()
    for line in text.splitlines():
        fields = line.split()
        if fields:
            result.add(fields[0])
    return result


def expand_dependency_filenames(initial: set[str],
                                file_to_internal: dict[str, str],
                                dependencies: dict[str, set[str]]) -> set[str]:
    internal_to_file = {}
    for filename, internal in file_to_internal.items():
        if internal in internal_to_file:
            raise ValueError(f"duplicate internal module name: {internal}")
        internal_to_file[internal] = filename
    expanded = set(initial)
    pending = list(initial)
    while pending:
        filename = pending.pop()
        internal = file_to_internal[filename]
        for dependency in dependencies[internal]:
            if dependency not in internal_to_file:
                raise ValueError(
                    f"{filename} has unavailable dependency: {dependency}"
                )
            dependency_file = internal_to_file[dependency]
            if dependency_file not in expanded:
                expanded.add(dependency_file)
                pending.append(dependency_file)
    return expanded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selected_module_directory", type=Path)
    parser.add_argument("kernel_build", type=Path)
    parser.add_argument("wlan_module", type=Path)
    parser.add_argument("--loaded-modules", type=Path,
                        help="saved /proc/modules from the stock-kernel boot")
    args = parser.parse_args()

    selected_paths = sorted(args.selected_module_directory.glob("*.ko"))
    built_paths = sorted(args.kernel_build.rglob("*.ko"))
    selected = unique_by_name(selected_paths)
    built = unique_by_name(built_paths)
    if len(selected) < 50 or len(built) < 50:
        raise SystemExit("module inventory is unexpectedly small")
    if args.wlan_module.name != "qca_cld3_wlan.ko":
        raise SystemExit("external WLAN output must be named qca_cld3_wlan.ko")

    abi = load_abi_module()
    covered, omitted = plan_closure(set(selected), set(built))
    available = dict(built)
    available["qca_cld3_wlan.ko"] = args.wlan_module
    available_info = {}
    file_to_internal = {}
    dependencies = {}
    for name, path in available.items():
        _, info = abi.read_module(path)
        internal = canonical_name(info.get("name", path.stem))
        available_info[name] = info
        file_to_internal[name] = internal
        dependencies[internal] = {
            canonical_name(value)
            for value in info.get("depends", "").split(",") if value
        }
    expanded = expand_dependency_filenames(covered, file_to_internal, dependencies)
    candidates = {name: available[name] for name in expanded}

    exports = abi.parse_symvers_text(
        (args.kernel_build / "Module.symvers").read_text()
    )
    internal_names = set()
    import_count = 0
    failures = []
    for name, path in sorted(candidates.items()):
        imports, info = abi.read_module(path)
        missing, mismatched = abi.audit(imports, exports)
        import_count += len(imports)
        internal_names.add(canonical_name(info.get("name", path.stem)))
        vermagic = info.get("vermagic", "")
        if missing or mismatched or not vermagic.startswith(RELEASE + " "):
            failures.append((name, len(missing), len(mismatched), vermagic))

    loaded_missing = set()
    if args.loaded_modules:
        loaded = parse_loaded(args.loaded_modules.read_text())
        loaded_missing = loaded - internal_names

    print(
        f"selected={len(selected)} coherent={len(candidates)} "
        f"omitted_unused={len(omitted)} imports={import_count} "
        f"abi_failures={len(failures)}"
    )
    if omitted:
        print("omitted_unused_modules=" + ",".join(sorted(omitted)))
    if args.loaded_modules:
        print(f"loaded_missing={len(loaded_missing)}")
        if loaded_missing:
            print("loaded_missing_modules=" + ",".join(sorted(loaded_missing)))
    for name, missing, mismatched, vermagic in failures:
        print(
            f"failure={name} missing={missing} mismatched={mismatched} "
            f"vermagic={vermagic}"
        )
    return 1 if failures or loaded_missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
