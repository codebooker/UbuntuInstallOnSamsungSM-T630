#!/usr/bin/env python3

from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_pd_mapper_deb.sh"


class PdMapperPackageBuilderTests(unittest.TestCase):
    def test_shell_and_pinned_source(self):
        subprocess.run(["sh", "-n", BUILDER], check=True)
        source = BUILDER.read_text(encoding="utf-8")
        self.assertIn("5ecd2fe926aca7abfe40724177f63b942cff3947", source)
        self.assertIn(
            "08972b8813d08da5e20d27e57c5989398a0b750be92cd4398b5b21190c6ccdd0",
            source,
        )
        self.assertIn("sha256sum -c", source)
        self.assertIn("-ffile-prefix-map=", source)
        self.assertIn("--build-id=sha1", source)

    def test_package_is_arm64_and_does_not_install_live(self):
        source = BUILDER.read_text(encoding="utf-8")
        self.assertIn("Architecture: arm64", source)
        self.assertIn("Depends: libc6, liblzma5, libqrtr1", source)
        self.assertNotIn("Depends: libc6, liblzma5, libqrtr-glib0", source)
        self.assertIn("libqrtr-dev", source)
        self.assertIn("0010-pd-mapper-directory-override.patch", source)
        patch = (ROOT / "patches/0010-pd-mapper-directory-override.patch").read_text()
        self.assertIn('!strcmp(argv[1], "--directory")', patch)
        self.assertIn("opendir(map_directory)", patch)
        self.assertIn("usr/local/sbin/t630-pd-mapper", source)
        self.assertNotIn("mv \"$build/t630-pd-mapper\" /usr/local", source)
        self.assertNotIn("cp \"$build/t630-pd-mapper\" /usr/local", source)


if __name__ == "__main__":
    unittest.main()
