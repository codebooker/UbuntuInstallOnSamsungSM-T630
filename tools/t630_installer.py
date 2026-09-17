#!/usr/bin/env python3
"""One guarded host entry point for the accepted SM-T630 install workflow."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
from typing import Optional, Sequence


TOOLS = Path(__file__).resolve().parent


def run_tool(name: str, arguments: Sequence[str] = ()) -> None:
    target = TOOLS / name
    if target.parent != TOOLS or not target.is_file() or target.is_symlink():
        raise RuntimeError(f"installer component is absent or unsafe: {name}")
    subprocess.run([sys.executable, str(target), *arguments], check=True)


def workflow(
        *, host_bundle: Optional[Path], tablet_bundle: Optional[str],
        staged: bool,
        verify_only: bool, prepare: bool, install: bool,
        acknowledge_stock_recovery: bool) -> None:
    if verify_only:
        if host_bundle is None:
            raise ValueError("--verify-only requires --host-bundle")
        if prepare or install or acknowledge_stock_recovery:
            raise ValueError("--verify-only cannot prepare or install")
        run_tool("finalize_installer_bundle.py", ("--verify", str(host_bundle)))
        print("INSTALL_ASSISTANT_COMPLETE: sealed host bundle verified; no tablet change")
        return

    if acknowledge_stock_recovery and not install:
        raise ValueError("--acknowledge-stock-recovery is only valid with --install")
    if install and not acknowledge_stock_recovery:
        raise ValueError("--install requires --acknowledge-stock-recovery")

    if staged:
        if not prepare and not install:
            raise ValueError("--staged requires --prepare or --install")
        if prepare:
            run_tool("prepare_staged_install.py")
    elif host_bundle is not None:
        if prepare:
            raise ValueError(
                "--prepare is for a bundle copied from mounted tablet linuxroot; "
                "host staging already requires the tablet-side read-only gate")
        run_tool("stage_installer_bundle.py", (str(host_bundle),))
    else:
        assert tablet_bundle is not None
        run_tool("stage_installer_bundle_local.py", (tablet_bundle,))
        if prepare or install:
            run_tool("prepare_staged_install.py")

    if install:
        run_tool("authorize_staged_install.py", ("--acknowledge-stock-recovery",))
        print("INSTALL_ASSISTANT_COMPLETE: installation verified; explicit reboot required")
    elif prepare:
        print("INSTALL_ASSISTANT_COMPLETE: final read-only gate passed; no format performed")
    else:
        print("INSTALL_ASSISTANT_COMPLETE: bundle staged in RAM; no device write")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--host-bundle", type=Path,
        help="sealed bundle directory on this computer")
    source.add_argument(
        "--tablet-bundle",
        help="canonical sealed-bundle path already below /run/ubuntu on the tablet")
    source.add_argument(
        "--staged", action="store_true",
        help="continue a previously verified bundle already in tablet RAM")
    parser.add_argument(
        "--verify-only", action="store_true",
        help="verify a host bundle and exit without connecting to the tablet")
    parser.add_argument(
        "--prepare", action="store_true",
        help="after tablet-local staging, stop Ubuntu, unmount linuxroot, and run the read-only gate")
    parser.add_argument(
        "--install", action="store_true",
        help="after all gates, request the existing typed destructive authorization")
    parser.add_argument(
        "--acknowledge-stock-recovery", action="store_true",
        help="confirm the matching deeply verified factory package is retained")
    args = parser.parse_args()
    try:
        workflow(
            host_bundle=args.host_bundle,
            tablet_bundle=args.tablet_bundle,
            staged=args.staged,
            verify_only=args.verify_only,
            prepare=args.prepare,
            install=args.install,
            acknowledge_stock_recovery=args.acknowledge_stock_recovery,
        )
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
