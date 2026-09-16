# Waydroid rendering performance (2026-09-16)

## Diagnosis

Android lag was caused by software rendering, not memory pressure. The physical
tablet still had roughly 2.8 GiB available, but Android SurfaceFlinger reported
`Mesa, llvmpipe` and consumed multiple CPU cores while animating. The Qualcomm
GPU remained idle. The initial 1920×1168 render target requires more than 2.2
million pixels to pass through Android SurfaceFlinger, nested GNOME, and the
Weston pixman parent for each frame.

The Waydroid container already received `/dev/kgsl-3d0`,
`/dev/dri/renderD128`, and `/dev/ion`. The missing acceleration was therefore
not a device-node or permission error.

## Rejected hardware paths

Two hardware trials were bounded and fully rolled back:

1. Waydroid's included Turnip/Freedreno Vulkan library recognizes a KGSL build,
   but it enumerated no GPU against this Samsung downstream kernel. Forcing
   Skia Vulkan caused SystemUI and Settings to abort with
   `Assertion failed: !gpuCount`.
2. The exact DZE3 stock vendor image supplied matching Adreno 642L EGL/GLES
   libraries. They loaded successfully from an isolated Waydroid vendor
   overlay but returned `EGL_BAD_DISPLAY` when paired with Waydroid's GBM
   gralloc. SurfaceFlinger correctly refused to start. The overlay, its property
   overrides, and the 1.1 GB lab image copy were removed.

A direct connection to the parent Weston compositor was also rejected. The
Waydroid composer repeatedly lost its Wayland client connection because the
parent does not provide the nested GNOME compatibility path expected by the
current integration.

None of these trials changed application or account data.

## Accepted software profile

The stable llvmpipe path was retained. Android's physical target was reduced to
1024×623 with a matching input viewport, and all three Android animation scales
were set to zero. A repeated, deterministic Settings scroll produced:

| Profile | Janky frames | p50 | p90 | p95 | p99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1280×779, animations 0.5× | 43.54% | 36 ms | 73 ms | 85 ms | 93 ms |
| 1024×623, animations off | 31.76% | 31 ms | 53 ms | 61 ms | 81 ms |

The Android boot, exact input viewport, stable `system_server`, empty clean-boot
crash buffer, and full GAPPS acceptance check passed after the final profile
was restored to the normal nested-GNOME session.

`t630-waydroid-runtime` 0.1.6 packages
`t630-waydroid-software-profile`. Its first `apply` stores only the previous
numeric width, height, and animation values in a root-only file. `restore`
returns those values. Neither path reads Android accounts or application data.
