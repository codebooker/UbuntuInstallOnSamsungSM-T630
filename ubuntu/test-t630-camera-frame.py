#!/usr/bin/python3
"""Capture volatile SM-T630 camera frames and report luma statistics.

This is a validation tool, not a camera application. It never retains an image:
the temporary raw stream is removed before exit, including on failure.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile


WIDTH = 640
HEIGHT = 480
FRAME_BYTES = WIDTH * HEIGHT * 3 // 2
INSTALL_ID = "SM-T630-T630XXSBDZE3-Ubuntu-v1"
RUN = "/usr/local/bin/t630-gnome-run"
CONTROL = "/usr/local/sbin/t630-camera-control"


def summarize_luma(luma):
    if len(luma) != WIDTH * HEIGHT:
        raise ValueError("unexpected luma-plane size")
    ordered = sorted(luma)
    count = len(ordered)
    total = sum(ordered)
    mean = total / count
    variance = sum((value - mean) ** 2 for value in ordered) / count
    return {
        "minimum": ordered[0],
        "p01": ordered[count // 100],
        "median": ordered[count // 2],
        "p99": ordered[count * 99 // 100],
        "maximum": ordered[-1],
        "mean": round(mean, 2),
        "standard_deviation": round(math.sqrt(variance), 2),
        "near_black_fraction": round(sum(value <= 4 for value in ordered) / count, 4),
        "near_white_fraction": round(sum(value >= 251 for value in ordered) / count, 4),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("camera", choices=("front", "rear"))
    args = parser.parse_args()

    if os.getuid() != 1000:
        raise SystemExit("Run through t630-gnome-run as the tablet user")
    if Path("/etc/t630-install-id").read_text().strip() != INSTALL_ID:
        raise SystemExit("Refusing an unrecognized device installation")

    runtime = Path(os.environ["XDG_RUNTIME_DIR"])
    if runtime != Path("/run/user/1000") or runtime.stat().st_uid != 1000:
        raise SystemExit("Unexpected tablet-user runtime directory")

    node = f"t630_{args.camera}_camera"
    fd, temporary = tempfile.mkstemp(prefix="t630-camera-validation-", suffix=".i420",
                                    dir=runtime)
    os.close(fd)
    path = Path(temporary)
    try:
        subprocess.run(["sudo", "-n", CONTROL, args.camera], check=True, timeout=75)
        subprocess.run([
            "gst-launch-1.0", "-q", "-e",
            "pipewiresrc", f"target-object={node}", "num-buffers=8", "!",
            f"video/x-raw,format=I420,width={WIDTH},height={HEIGHT},framerate=30/1", "!",
            "filesink", f"location={path}",
        ], check=True, timeout=20)
        raw = path.read_bytes()
        if not raw or len(raw) % FRAME_BYTES:
            raise RuntimeError(f"unexpected raw capture size: {len(raw)}")
        frames = len(raw) // FRAME_BYTES
        start = (frames - 1) * FRAME_BYTES
        result = {
            "camera": args.camera,
            "frames": frames,
            "width": WIDTH,
            "height": HEIGHT,
            "luma": summarize_luma(raw[start:start + WIDTH * HEIGHT]),
            "interpretation": (
                "frame has measurable contrast"
                if len(set(raw[start:start + WIDTH * HEIGHT])) > 8
                else "frame is nearly uniform; aim the lens at a lit, detailed target"
            ),
        }
    finally:
        path.unlink(missing_ok=True)
        subprocess.run(["sudo", "-n", CONTROL, "disable"], check=True,
                       timeout=15, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    # Never report a capture pass before exclusive camera cleanup also passes.
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
