#!/usr/bin/env python3
"""Build and locally sign the minimal SM-T630 Android OS-switch button."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "android-switcher"
DEFAULT_SDK = Path("/opt/homebrew/share/android-commandlinetools")
DEFAULT_JAVA = Path("/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home")


def run(*args: object, env: dict[str, str] | None = None) -> None:
    subprocess.run([str(arg) for arg in args], check=True, env=env)


def build(output: Path, keystore: Path, sdk: Path, java_home: Path) -> None:
    tools = sdk / "build-tools/35.0.1"
    android_jar = sdk / "platforms/android-35/android.jar"
    required = [tools / name for name in ("aapt2", "d8", "zipalign", "apksigner")]
    required.append(android_jar)
    required.append(java_home / "bin/javac")
    required.append(java_home / "bin/keytool")
    for path in required:
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    keystore.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["JAVA_HOME"] = str(java_home)
    environment["PATH"] = f"{java_home / 'bin'}:{environment.get('PATH', '')}"
    if not keystore.exists():
        run(
            java_home / "bin/keytool", "-genkeypair", "-noprompt",
            "-keystore", keystore, "-storetype", "PKCS12",
            "-storepass", "t630-local-builder", "-keypass", "t630-local-builder",
            "-alias", "t630-switcher", "-keyalg", "RSA", "-keysize", "3072",
            "-validity", "3650", "-dname", "CN=SM-T630 Local Switcher",
            env=environment,
        )
        keystore.chmod(0o600)
    with tempfile.TemporaryDirectory(prefix="t630-android-switcher-") as directory:
        work = Path(directory)
        compiled = work / "compiled.zip"
        unsigned = work / "unsigned.apk"
        aligned = work / "aligned.apk"
        classes = work / "classes"
        dex = work / "dex"
        classes.mkdir()
        dex.mkdir()
        run(tools / "aapt2", "compile", "--dir", SOURCE / "res", "-o", compiled,
            env=environment)
        run(
            tools / "aapt2", "link", "-o", unsigned, "-I", android_jar,
            "--manifest", SOURCE / "AndroidManifest.xml", "--min-sdk-version", "28",
            "--target-sdk-version", "35", "--version-code", "1",
            "--version-name", "0.1.0", compiled, env=environment,
        )
        java_sources = sorted((SOURCE / "src").rglob("*.java"))
        run(
            java_home / "bin/javac", "-encoding", "UTF-8", "-source", "8", "-target", "8",
            "-classpath", android_jar, "-d", classes, *java_sources, env=environment,
        )
        class_files = sorted(classes.rglob("*.class"))
        run(
            tools / "d8", "--min-api", "28", "--lib", android_jar,
            "--output", dex, *class_files, env=environment,
        )
        run("zip", "-q", "-j", unsigned, dex / "classes.dex", env=environment)
        run(tools / "zipalign", "-p", "-f", "4", unsigned, aligned, env=environment)
        temporary_output = output.with_suffix(".apk.new")
        shutil.copyfile(aligned, temporary_output)
        run(
            tools / "apksigner", "sign", "--ks", keystore,
            "--ks-pass", "pass:t630-local-builder", "--key-pass", "pass:t630-local-builder",
            "--ks-key-alias", "t630-switcher", temporary_output, env=environment,
        )
        run(tools / "apksigner", "verify", "--verbose", temporary_output, env=environment)
        temporary_output.chmod(0o644)
        temporary_output.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output/t630-os-switcher-0.1.0.apk")
    parser.add_argument("--keystore", type=Path,
                        default=ROOT / "output/private-t630-switcher-keystore.p12")
    parser.add_argument("--sdk", type=Path,
                        default=Path(os.environ.get("ANDROID_SDK_ROOT", DEFAULT_SDK)))
    parser.add_argument("--java-home", type=Path, default=DEFAULT_JAVA)
    args = parser.parse_args()
    build(args.output.resolve(), args.keystore.resolve(), args.sdk.resolve(),
          args.java_home.resolve())
    print(args.output)


if __name__ == "__main__":
    main()
