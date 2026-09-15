from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class PenProximityTrialTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'C compiler unavailable')
    def test_proximity_lifecycle_preserves_motion_and_touch(self):
        with tempfile.TemporaryDirectory(prefix='t630-pen-unit-') as directory:
            binary = str(Path(directory) / 'probe')
            subprocess.run([shutil.which('cc'), '-Wall', '-Wextra', '-Werror',
                            str(Path(__file__).with_suffix('.c')), '-o', binary],
                           check=True, capture_output=True, timeout=30)
            subprocess.run([binary], check=True, capture_output=True, timeout=5)
