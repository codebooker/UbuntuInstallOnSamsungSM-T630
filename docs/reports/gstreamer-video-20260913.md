# GStreamer and WebKit video investigation — 2026-09-13

This report records a process-scoped extension of the SM-T630 V4L2 decoder
adapter. It does **not** make WebKit the default browser and does not enable an
unsandboxed browser launcher.

## Driver compatibility fixes

The stock `msm_vidc_vdec` node is not compatible with generic GStreamer as
reported by the kernel ABI:

- `VIDIOC_ENUM_FRAMESIZES` succeeds forever for nonzero indexes and returns a
  zeroed stepwise range. The adapter now terminates enumeration after index 0
  and reports the common safe DZE3 yupik v0 capability range (96–4096 for
  H.264, HEVC and VP9; MPEG-2 capped at 1920×1088).
- The default capture format is Qualcomm UBWC (`Q128`). The adapter selects
  linear NV12 and takes the dimensions from the already-configured compressed
  queue instead of the stale 320×240 capture default.
- The driver does not implement `VIDIOC_TRY_FMT`. In GStreamer mode the adapter
  answers the probe without changing live decoder state and clamps probes to
  96–4096. This prevents GStreamer's 32768×32768 caps probe from reconfiguring
  and overloading the hardware.
- Qualcomm's second capture plane is decoder extradata, not NV12 chroma.
  GStreamer otherwise treats it as an image plane and copies beyond its 16 KiB
  allocation. In `T630_V4L2_GSTREAMER=1` mode the adapter exposes one
  contiguous NV12 image plane while keeping the extradata allocation internal.
- The dequeue path compacts the vendor's 512-scanline chroma padding and reports
  the compact NV12 byte extent instead of the entire padded allocation.
- Samsung signals decoder end-of-stream with Qualcomm's private
  `V4L2_BUF_FLAG_EOS` (`0x10000000`). The adapter translates it to the standard
  `V4L2_BUF_FLAG_LAST` expected after `VIDIOC_DECODER_CMD(STOP)`.

The mode remains opt-in and process scoped:

```sh
T630_V4L2_GSTREAMER=1 \
LD_PRELOAD=/usr/local/lib/t630/t630-v4l2-compat.so \
gst-launch-1.0 ... v4l2h264dec ...
```

The adapter still checks the exact `msm_vidc_driver` / `msm_vidc_vdec` identity
before translating any V4L2 request. It is never preloaded system-wide.

## Live results

On boot `e3fdbec7-82e2-483a-b60e-41673728ffa5`:

- GStreamer decoded all 60 frames of a generated 1280×720 H.264 stream through
  `v4l2h264dec`, received the translated standard end-of-stream marker and
  exited normally in 254 ms without a bounded sink workaround.
- A captured 1280×720 NV12 frame matched GStreamer's software decode byte for
  byte after applying each buffer's advertised plane offsets and strides.
- GStreamer's `v4l2vp9dec` decoded and drained a 60-frame 1280×720 VP9 stream in
  235 ms. Its complete 82,944,000-byte I420 output matched `avdec_vp9` byte for
  byte after normal video-format conversion.
- The existing FFmpeg adapter path decoded all 60 frames through
  `h264_v4l2m2m`; its complete NV12 output matched software decode byte for
  byte.
- The installed adapter SHA256 after these changes is
  `28fe0677bed5b00d42be4baa65defff907f0e06a149111964defd04550fe7fb6`.
- Neither decoder test added a VIDC overload/state error, GPU fault, kernel
  oops, panic or watchdog marker.

Before the private-to-standard EOS translation, the same unbounded pipeline
waited indefinitely after delivering its last frame. The ordinary finite-file
path now drains and exits without a timeout or special sink configuration.

## Real browser result and security boundary

Epiphany 46.5 was used only for a live integration test. A private WebKit
process played a local looping H.264 MP4 and held `/dev/video32`, proving that
WebKit selected the hardware GStreamer decoder rather than merely passing a
standalone pipeline test.

The normal browser cannot start on this stock Samsung kernel because the exact
kernel configuration has `CONFIG_USER_NS` disabled. WebKit's Bubblewrap helper
fails while creating its user namespace. A temporary setuid-Bubblewrap test did
not solve WebKit's explicit user-namespace request and its mode was restored to
0755 immediately. Disabling the WebKit sandbox allowed the integration test,
but that is not an acceptable general web-browsing default and no such launcher
is installed or documented as a user recommendation.

Firefox therefore remains the safe default browser. Browser hardware video is
verified at the decoder/application boundary but remains unshipped until there
is a reviewed sandbox solution (or a replacement kernel with user namespaces).

## Cold-boot persistence

After installing the final adapter, an ordinary `/bin/stop-ubuntu reboot` was
issued from the retained USB recovery environment so the Ubuntu filesystem was
stopped and unmounted first. Fresh boot
`4e65451d-b0b6-4c0d-90e5-5d11a28306a9` automatically restored Weston, GNOME,
Wi-Fi, Bluetooth with both audio profiles, the 30% speaker sink, the microphone
source, UPower battery reporting, SensorProxy and the remote screen service.
NetworkManager handled the Wi-Fi interface appearing as `wlp1s0` rather than
the previous boot's `wlan0`.

The installed adapter retained its exact expected SHA256. A normal UID 1000
process then repeated both 60-frame 1280×720 tests: FFmpeg hardware output again
matched software NV12 byte for byte, and the unbounded GStreamer pipeline again
drained to EOS normally through `v4l2h264dec`. The camera compatibility stack
was stopped, shared device permissions remained valid, package audit was clean,
and the expanded kernel-fault check reported zero markers.
