#!/usr/bin/env python3

import importlib.util
import subprocess
import tempfile
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
        self.assertIn("super_device=$(cat /sys/class/block/sda26/dev)", mounts)
        self.assertIn('linear $super_device 2048', mounts)
        self.assertNotIn("linear 259:10", mounts)

    def test_camera_control_bounds_owned_group_teardown(self):
        control = (ROOT / "ubuntu/t630-camera-control").read_text()
        self.assertIn('while pid_matches "$file" "$marker"', control)
        self.assertIn('kill -KILL -- "-$pid"', control)
        self.assertIn('test "$attempt" -lt 16', control)
        self.assertIn("cmdline=$( { tr", control)
        self.assertIn("} 2>/dev/null) || return 1", control)
        self.assertIn("flock -n 9", control)
        self.assertIn("exit 75", control)
        self.assertIn("/usr/bin/gst-launch-1.0", control)
        self.assertIn("ACameraCaptureSession_close()", control)
        self.assertIn("ps -eo pid=,pgid=,exe= | while read", control)
        self.assertNotIn("done < <(", control)
        disable = control.index('if [ "$action" = disable ]')
        restart = control.index('if ! pid_matches /run/t630-camera-stack.pid')
        branch = control[disable:restart]
        self.assertIn('stop_group /run/t630-camera-bridge.pid', branch)
        self.assertIn('stop_group /run/t630-camera-stack.pid', branch)
        self.assertIn('rm -f /run/t630-camera-ready', branch)
        self.assertIn('bridge_attempt=0', control)
        self.assertIn('CameraService and the downstream CDM/IFE driver', control)

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
        self.assertIn("ACAMERA_CONTROL_AWB_AVAILABLE_MODES", capture)
        self.assertIn("produced no", capture)
        self.assertNotIn("rear_awb_mode", capture)
        self.assertIn("ACAMERA_CONTROL_AF_MODE_CONTINUOUS_PICTURE", capture)
        self.assertIn("ACAMERA_CONTROL_AF_MODE_OFF", capture)
        self.assertIn("rear_exposure_ns = 30000000", capture)
        self.assertIn("rear_sensitivity = 800", capture)
        self.assertIn('dlsym(library, "ABinderProcess_startThreadPool")', capture)
        self.assertIn("capture metadata: exposure=", capture)
        self.assertIn('strcmp(argv[1], "--describe")', capture)
        self.assertIn("ACAMERA_FLASH_INFO_AVAILABLE", capture)
        self.assertIn("ACAMERA_CONTROL_AF_AVAILABLE_MODES", capture)
        self.assertIn("ACAMERA_SCALER_AVAILABLE_STREAM_CONFIGURATIONS", capture)
        self.assertIn("ACAMERA_CONTROL_AE_AVAILABLE_TARGET_FPS_RANGES", capture)
        self.assertIn("ACAMERA_CONTROL_AF_STATE", capture)
        self.assertIn("ACAMERA_FLASH_STATE", capture)
        self.assertIn("current_af_state != last_af_state", capture)
        self.assertIn("ACAMERA_COLOR_CORRECTION_GAINS", capture)
        self.assertIn("gains=%.3f,%.3f,%.3f,%.3f", capture)
        self.assertIn("signal(SIGPIPE, SIG_IGN)", capture)

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
        self.assertIn('width=720', bridge)
        self.assertIn('height=480', bridge)
        self.assertIn('t630-yuv-tune "$width" "$height" 900 1320', rear)
        self.assertIn("/home/tablet/.config/t630-camera/rear-color", rear)
        self.assertIn('color_filter=(cat)', front)

    def test_rear_color_filter_is_bounded_and_streaming(self):
        source = (ROOT / "camera/t630-yuv-tune.c").read_text()
        build = (ROOT / "tools/build_camera_color_filter.sh").read_text()
        self.assertIn("red-permille blue-permille", source)
        self.assertIn("red_gain < 500", source)
        self.assertIn("blue_gain > 2000", source)
        self.assertIn("signal(SIGPIPE, SIG_IGN)", source)
        self.assertIn("truncated I420 frame", source)
        self.assertIn("load_color_offset", source)
        self.assertIn("frame_number % 15", source)
        self.assertIn("-Werror", build)

    def test_color_slider_is_bounded_and_atomic(self):
        slider = (ROOT / "ubuntu/t630-camera-color.py").read_text()
        desktop = (ROOT / "ubuntu/t630-camera-color.desktop").read_text()
        self.assertIn("Gtk.Scale.new_with_range", slider)
        self.assertIn("-100, 100, 1", slider)
        self.assertIn('os.replace(temporary, SETTINGS)', slider)
        self.assertIn('"Warmer"', slider)
        self.assertIn('"Cooler"', slider)
        self.assertIn("Exec=/usr/local/bin/t630-camera-color", desktop)

    def test_rear_color_filter_reduces_yellow_chroma(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "t630-yuv-tune"
            subprocess.run([
                "cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                str(ROOT / "camera/t630-yuv-tune.c"), "-o", str(binary),
            ], check=True)
            # One 2x2 I420 block: neutral luma with low U/high V is yellow.
            frame = bytes([128, 128, 128, 128, 90, 150])
            result = subprocess.run(
                [str(binary), "2", "2", "920", "1250"],
                input=frame, check=True, capture_output=True).stdout
            self.assertEqual(len(result), len(frame))
            self.assertGreater(result[4], frame[4])
            self.assertLess(result[5], frame[5])

            setting = Path(directory) / "color"
            setting.write_text("20\n")
            cooler = subprocess.run(
                [str(binary), "2", "2", "900", "1320", str(setting)],
                input=frame, check=True, capture_output=True).stdout
            self.assertGreater(cooler[4], result[4])
            self.assertLess(cooler[5], result[5])

if __name__ == "__main__":
    unittest.main()
