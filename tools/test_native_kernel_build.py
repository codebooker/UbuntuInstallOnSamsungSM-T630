import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools/check_native_kernel.py"
SPEC = importlib.util.spec_from_file_location("check_native_kernel", SOURCE)
checker = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(checker)


class NativeKernelBuildTests(unittest.TestCase):
    def test_build_script_is_valid_and_excludes_container_config(self):
        script = ROOT / "tools/build_native_kernel.sh"
        subprocess.run(["bash", "-n", script], check=True)
        text = script.read_text()
        patch_block = text.split("native_patches=(", 1)[1].split(")", 1)[0]
        self.assertNotIn("0009", patch_block)
        self.assertIn("0018", patch_block)
        self.assertIn("check_native_kernel.py", text)

    def test_native_config_gate(self):
        required = "\n".join(f"{key}={value}" for key, value in checker.REQUIRED.items())
        deferred = "\n".join(f"# {key} is not set" for key in checker.DEFERRED)
        with tempfile.TemporaryDirectory() as temporary:
            config = Path(temporary) / ".config"
            config.write_text(required + "\n" + deferred + "\n")
            checker.validate(config)
            config.write_text(required + "\nCONFIG_USER_NS=y\n")
            with self.assertRaises(SystemExit):
                checker.validate(config)


if __name__ == "__main__":
    unittest.main()
