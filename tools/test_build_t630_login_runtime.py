from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/build_t630_login_runtime.sh"


class LoginRuntimeBuildTests(unittest.TestCase):
    def test_builder_is_pinned_staged_and_non_installing(self):
        subprocess.run(["sh", "-n", SCRIPT], check=True)
        text = SCRIPT.read_text()
        self.assertIn("v255.27.tar.gz", text)
        self.assertIn("1ef0dffaad77e8d8ded047895fc5e60b", text)
        self.assertIn("gdm3_46.2.orig.tar.xz", text)
        self.assertIn("4ee345422a16537150cd842450cda52b", text)
        self.assertIn("dconf-cli", text)
        self.assertIn("T630_LOGIN_DOWNLOAD_CACHE", text)
        self.assertIn('DESTDIR="$build/stage"', text)
        self.assertIn("gdm-auth-only-greeter.patch", text)
        self.assertIn("t630-desktop-runtime (>= 0.1.5)", text)
        self.assertIn('"$build/pkgconfig/libelogind.pc"', text)
        self.assertIn("libdir=$build/stage/opt/t630/elogind-255.27/lib", text)
        self.assertIn("t630-login-runtime_0.1.2_arm64.deb", text)
        self.assertIn("Version: 0.1.2", text)
        self.assertIn("t630-login-runtime/copyright", text)
        self.assertIn("dpkg-divert", text)
        self.assertNotIn("dpkg -i", text)

    def test_runtime_has_safe_private_configs(self):
        login = (ROOT / "ubuntu/t630-gdm-auth-only.conf").read_text()
        self.assertIn("ShowLocalGreeter=false", login)
        self.assertIn("Enable=false", login)
        elogind = (ROOT / "ubuntu/t630-elogind-lab.conf").read_text()
        self.assertIn("HandlePowerKey=ignore", elogind)
        self.assertIn("IdleAction=ignore", elogind)
        sleep = (ROOT / "ubuntu/t630-elogind-sleep.conf").read_text()
        self.assertIn("AllowSuspend=no", sleep)
        pam = (ROOT / "ubuntu/t630-common-session").read_text()
        self.assertIn("pam_succeed_if.so service = sshd uid = 0 quiet", pam)


if __name__ == "__main__":
    unittest.main()
