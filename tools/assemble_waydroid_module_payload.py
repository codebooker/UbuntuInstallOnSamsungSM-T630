#!/usr/bin/env python3
"""Assemble a stripped, audited SM-T630 Waydroid module payload offline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess


PROJECT_NAME = "gtact4prowifi"
PROJECT_AUDIO_HEADER = "lahaina_gtact4pro.h"


def load_sibling(name: str):
    source = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location("t630_" + source.stem, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def choose_modules(selected: dict[str, Path], built: dict[str, Path],
                   wlan: Path, closure_module) -> tuple[dict[str, Path], set[str]]:
    covered, omitted = closure_module.plan_closure(set(selected), set(built))
    chosen = {name: built[name] for name in covered if name in built}
    chosen["qca_cld3_wlan.ko"] = wlan
    return chosen, omitted


def filtered_module_list(text: str, chosen: set[str]) -> str:
    lines = [line for line in text.splitlines() if line.strip() in chosen]
    return "\n".join(lines) + ("\n" if lines else "")


def generated_modules_dep(records: list[dict]) -> str:
    closure = load_sibling("audit_waydroid_module_closure.py")
    internal_to_file = {
        closure.canonical_name(item["internal_name"]): item["file"]
        for item in records
    }
    lines = []
    for item in sorted(records, key=lambda value: value["file"]):
        dependencies = [
            closure.canonical_name(value)
            for value in item["depends"].split(",") if value
        ]
        missing = set(dependencies) - internal_to_file.keys()
        if missing:
            raise ValueError(
                f"{item['file']} depends on unavailable modules: "
                + ",".join(sorted(missing))
            )
        paths = " ".join(
            "/vendor/lib/modules/" + internal_to_file[value]
            for value in dependencies
        )
        lines.append(f"/vendor/lib/modules/{item['file']}:"
                     + (" " + paths if paths else ""))
    return "\n".join(lines) + "\n"


def verify_project_profile(kernel_build: Path) -> Path:
    """Reject modules compiled with another Samsung product's audio profile."""
    command = kernel_build / "techpack/audio/asoc/.lahaina.o.cmd"
    if not command.is_file() or command.is_symlink():
        raise ValueError(f"missing machine-driver build command: {command}")
    text = command.read_text()
    expected = f"/techpack/audio/config/{PROJECT_AUDIO_HEADER}"
    if expected not in text:
        raise ValueError(
            "machine driver was not built for PROJECT_NAME=" + PROJECT_NAME
        )
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selected_module_directory", type=Path)
    parser.add_argument("kernel_build", type=Path)
    parser.add_argument("wlan_module", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()

    if args.output_directory.exists():
        raise SystemExit("output directory already exists")
    if not args.output_directory.is_absolute():
        raise SystemExit("output directory must be absolute")
    if args.wlan_module.name != "qca_cld3_wlan.ko":
        raise SystemExit("WLAN module must be named qca_cld3_wlan.ko")
    strip = shutil.which("llvm-strip")
    if not strip:
        raise SystemExit("llvm-strip is required")

    profile_command = verify_project_profile(args.kernel_build)

    closure = load_sibling("audit_waydroid_module_closure.py")
    abi = load_sibling("audit_kernel_module_abi.py")
    selected = closure.unique_by_name(
        sorted(args.selected_module_directory.glob("*.ko"))
    )
    built = closure.unique_by_name(sorted(args.kernel_build.rglob("*.ko")))
    if len(selected) < 50 or len(built) < 50:
        raise SystemExit("module inventory is unexpectedly small")
    exports = abi.parse_symvers_text(
        (args.kernel_build / "Module.symvers").read_text()
    )
    chosen, omitted = choose_modules(selected, built, args.wlan_module, closure)
    available = dict(built)
    available["qca_cld3_wlan.ko"] = args.wlan_module
    file_to_internal = {}
    dependencies = {}
    for name, path in available.items():
        _, info = abi.read_module(path)
        internal = closure.canonical_name(info.get("name", path.stem))
        file_to_internal[name] = internal
        dependencies[internal] = {
            closure.canonical_name(value)
            for value in info.get("depends", "").split(",") if value
        }
    expanded = closure.expand_dependency_filenames(
        set(chosen), file_to_internal, dependencies
    )
    chosen = {name: available[name] for name in expanded}

    staging = Path(str(args.output_directory) + ".staging")
    if staging.exists():
        raise SystemExit("staging directory already exists")
    staging.mkdir(parents=True)
    try:
        records = []
        for name, source in sorted(chosen.items()):
            destination = staging / name
            subprocess.run(
                [strip, "--strip-debug", "-o", destination, source], check=True
            )
            imports, info = abi.read_module(destination)
            missing, mismatched = abi.audit(imports, exports)
            vermagic = info.get("vermagic", "")
            if (missing or mismatched
                    or not vermagic.startswith(closure.RELEASE + " ")):
                raise ValueError(f"ABI validation failed after stripping: {name}")
            records.append({
                "file": name,
                "sha256": digest(destination),
                "size": destination.stat().st_size,
                "imports": len(imports),
                "internal_name": info.get("name", ""),
                "depends": info.get("depends", ""),
            })
        metadata = {}
        module_load = filtered_module_list(
            (args.selected_module_directory / "modules.load").read_text(),
            set(chosen),
        )
        listed = set(module_load.splitlines())
        build_only = sorted(set(chosen) - set(selected) - listed)
        module_load += "".join(name + "\n" for name in build_only)
        generated = {
            "modules.dep": generated_modules_dep(records),
            "modules.load": module_load,
        }
        metadata_sources = {
            "modules.alias": None,
            "modules.softdep": None,
            "modules.blocklist": None,
        }
        for name, text in generated.items():
            destination = staging / name
            destination.write_text(text)
            metadata[name] = {
                "sha256": digest(destination),
                "size": destination.stat().st_size,
            }
        for name, transform in metadata_sources.items():
            source = args.selected_module_directory / name
            if not source.is_file() or source.is_symlink():
                raise ValueError(f"missing module metadata: {name}")
            destination = staging / name
            shutil.copyfile(source, destination)
            metadata[name] = {
                "sha256": digest(destination),
                "size": destination.stat().st_size,
            }
        manifest = {
            "format": 1,
            "device": "SM-T630",
            "firmware": "T630XXSBDZE3",
            "project_name": PROJECT_NAME,
            "audio_profile_header": PROJECT_AUDIO_HEADER,
            "audio_profile_command_sha256": digest(profile_command),
            "kernel_release": closure.RELEASE,
            "module_symvers_sha256": digest(args.kernel_build / "Module.symvers"),
            "selected_module_count": len(selected),
            "coherent_module_count": len(records),
            "omitted_unused_modules": sorted(omitted),
            "metadata": metadata,
            "modules": records,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        )
        os.replace(staging, args.output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    print(
        f"Assembled {len(chosen)} coherent modules; omitted "
        f"{len(omitted)} explicitly permitted unused modules."
    )
    print(f"Manifest: {args.output_directory / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
