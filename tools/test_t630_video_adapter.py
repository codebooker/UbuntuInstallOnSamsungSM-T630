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
        self.assertIn(
            "T630_V4L2_GSTREAMER",
            source,
        )

    def test_broken_frame_size_enumeration_is_bounded(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        self.assertIn("request == VIDIOC_ENUM_FRAMESIZES", source)
        self.assertIn("if (sizes->index != 0)", source)
        self.assertIn("sizes->stepwise.min_width = 96", source)
        self.assertIn("sizes->stepwise.max_width = max_width", source)
        self.assertIn("max_width = 1920", source)

    def test_default_ubwc_capture_is_changed_to_linear_nv12(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        self.assertIn("request == VIDIOC_G_FMT", source)
        self.assertIn("get_linear_capture_format", source)
        self.assertIn("format->fmt.pix_mp.pixelformat = V4L2_PIX_FMT_NV12", source)
        self.assertIn("V4L2_BUF_TYPE_VIDEO_OUTPUT_MPLANE", source)
        self.assertIn("format->fmt.pix_mp.width = output.fmt.pix_mp.width", source)

    def test_gstreamer_probe_does_not_reconfigure_live_decoder(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        self.assertIn("emulate_gstreamer_try_format", source)
        self.assertIn("pixels->width > 4096", source)
        self.assertIn("pixels->height > 4096", source)
        block = source.split("static int emulate_gstreamer_try_format", 1)[1]
        block = block.split("static struct decoder_state", 1)[0]
        self.assertNotIn("VIDIOC_S_FMT", block)

    def test_gstreamer_sees_one_nv12_plane_not_qualcomm_extradata(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        self.assertIn("format->fmt.pix_mp.num_planes = 1", source)
        self.assertIn(
            "buffer->type == V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE ?\n"
            "                     1 : num_planes",
            source,
        )

    def test_capture_dequeue_reports_compact_nv12_extent(self):
        source = (ROOT / "tools/t630_v4l2_probe.c").read_text()
        block = source.split("static int translate_dqbuf", 1)[1]
        block = block.split("__attribute__((constructor))", 1)[0]
        self.assertIn(
            "planes[0].bytesused = target_offset + chroma_size", block
        )

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
