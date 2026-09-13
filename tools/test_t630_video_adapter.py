import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VideoAdapterTests(unittest.TestCase):
    def test_adapter_is_scoped_and_exact_device_guarded(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        self.assertIn('strcmp((const char *)caps.driver, "msm_vidc_driver") == 0', source)
        self.assertIn('strcmp((const char *)caps.card, "msm_vidc_vdec") == 0', source)
        self.assertIn("V4L2_MEMORY_USERPTR", source)
        self.assertIn("ION_SYSTEM_HEAP_ID 25", source)
        self.assertIn("y_scanlines = (height + 511U) & ~511U", source)
        self.assertIn("memmove", source)

    def test_player_uses_adapter_with_software_fallback(self):
        launcher = (ROOT / "ubuntu/t630-video-player").read_text()
        self.assertIn("LD_PRELOAD", launcher)
        self.assertIn("h264_v4l2m2m", launcher)
        self.assertIn("vp9_v4l2m2m", launcher)
        self.assertNotIn("hevc_v4l2m2m", launcher)
        self.assertNotIn("mpeg2_v4l2m2m", launcher)
        decoder_list = next(line for line in launcher.splitlines() if "--vd=" in line)
        self.assertFalse(decoder_list.rstrip().endswith("-"))

    def test_video_nodes_are_not_world_writable(self):
        mdev = (ROOT / "ubuntu/mdev.conf").read_text()
        self.assertIn("video3[23] 0:994 660", mdev)
        self.assertNotIn("video3[23] 0:0 666", mdev)


if __name__ == "__main__":
    unittest.main()
