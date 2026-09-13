#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "ubuntu/test-t630-camera-frame.py"
SPEC = importlib.util.spec_from_file_location("camera_frame", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CameraFrameValidationTests(unittest.TestCase):
    def test_luma_statistics(self):
        pixels = bytes([0, 10, 20, 255]) * (MODULE.WIDTH * MODULE.HEIGHT // 4)
        result = MODULE.summarize_luma(pixels)
        self.assertEqual(result["minimum"], 0)
        self.assertEqual(result["maximum"], 255)
        self.assertEqual(result["median"], 20)
        self.assertEqual(result["mean"], 71.25)
        self.assertEqual(result["near_black_fraction"], 0.25)
        self.assertEqual(result["near_white_fraction"], 0.25)

    def test_capture_is_volatile_and_exactly_scoped(self):
        text = SOURCE.read_text()
        self.assertIn('choices=("front", "rear")', text)
        self.assertIn('/run/user/1000', text)
        self.assertIn('path.unlink(missing_ok=True)', text)
        self.assertIn('["sudo", "-n", CONTROL, "disable"]', text)
        self.assertIn('check=True', text)
        self.assertLess(text.index('CONTROL, "disable"'),
                        text.index('print(json.dumps(result'))
        self.assertNotIn("/data/", text)

    def test_camera_rescan_reapplies_desktop_permissions(self):
        mounts = (ROOT / "camera/t630-camera-mounts.sh").read_text()
        nodes = mounts.index("python3 /usr/local/share/t630/t630-camera-nodes.py")
        repair = mounts.index("python3 /usr/local/share/t630/t630-device-permissions.py")
        self.assertGreater(repair, nodes)
        self.assertNotIn("mdev -s", mounts)
        self.assertNotIn("chmod 666 /dev/null", mounts)

    def test_camera_control_bounds_owned_group_teardown(self):
        control = (ROOT / "ubuntu/t630-camera-control").read_text()
        self.assertIn('while pid_matches "$file" "$marker"', control)
        self.assertIn('kill -KILL -- "-$pid"', control)
        self.assertIn('test "$attempt" -lt 16', control)
        self.assertIn("cmdline=$( { tr", control)
        self.assertIn("} 2>/dev/null) || return 1", control)
        disable = control.index('if [ "$action" = disable ]')
        restart = control.index('if ! pid_matches /run/t630-camera-stack.pid')
        branch = control[disable:restart]
        self.assertIn('stop_group /run/t630-camera-bridge.pid', branch)
        self.assertIn('stop_group /run/t630-camera-stack.pid', branch)
        self.assertIn('rm -f /run/t630-camera-ready', branch)
        self.assertIn('bridge_attempt=0', control)
        self.assertIn('ACAMERA_ERROR_CAMERA_IN_USE', control)

    def test_camera_launcher_keeps_bridge_for_existing_snapshot(self):
        launcher = (ROOT / "ubuntu/t630-camera-app").read_text()
        self.assertIn('gsettings set org.gnome.Snapshot is-maximized true', launcher)
        self.assertIn('$XDG_RUNTIME_DIR/t630-camera-app.lock', launcher)
        self.assertIn('if ! flock -n 8', launcher)
        self.assertIn('pgrep -u "$(id -u)" -xo snapshot', launcher)
        self.assertIn('/proc/$snapshot_pid/exe', launcher)
        self.assertIn('while kill -0 "$snapshot_pid"', launcher)
        self.assertLess(launcher.index('sudo -n /usr/local/sbin/t630-camera-control'),
                        launcher.index('pgrep -u "$(id -u)" -xo snapshot'))

    def test_capture_uses_preview_auto_exposure(self):
        capture = (ROOT / "camera/t630-camera-capture.c").read_text()
        self.assertIn('strcmp(camera_id, "0") == 0 ? TEMPLATE_STILL_CAPTURE : TEMPLATE_PREVIEW', capture)
        self.assertIn("zero-filled buffers with TEMPLATE_PREVIEW", capture)
        self.assertIn("ACAMERA_CONTROL_MODE_AUTO", capture)
        self.assertIn("ACAMERA_CONTROL_AE_MODE_OFF : ACAMERA_CONTROL_AE_MODE_ON", capture)
        self.assertIn("ACAMERA_CONTROL_AWB_MODE_AUTO", capture)
        self.assertIn("ACAMERA_CONTROL_AF_MODE_CONTINUOUS_VIDEO", capture)
        self.assertIn("rear_exposure_ns = 60000000", capture)
        self.assertIn("rear_sensitivity = 1600", capture)
        self.assertIn('dlsym(library, "ABinderProcess_startThreadPool")', capture)
        self.assertIn("capture metadata: exposure=", capture)

    def test_ndk_build_includes_capture_client(self):
        build = (ROOT / "tools/build_camera_sensor_bridge.sh").read_text()
        self.assertIn('camera/t630-camera-capture.c', build)
        self.assertIn('-lcamera2ndk -lmediandk', build)
        self.assertIn('-o "$output_dir/t630-camera-capture"', build)

    def test_rear_bridge_has_scoped_tone_lift(self):
        bridge = (ROOT / "ubuntu/t630-camera-bridge").read_text()
        front = bridge[bridge.index("    front)"):bridge.index("    rear)")]
        rear = bridge[bridge.index("    rear)"):bridge.index("    *)")]
        self.assertIn("image_filter=", front)
        self.assertNotIn("gamma=", front)
        self.assertIn("gamma gamma=2.5", rear)

if __name__ == "__main__":
    unittest.main()
