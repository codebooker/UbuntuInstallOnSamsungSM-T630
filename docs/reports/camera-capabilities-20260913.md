# Camera capabilities, autofocus, and preview ceiling

Date: 2026-09-13. Device: one physical SM-T630 on the exact
`T630XXSBDZE3` baseline. Tests retained no camera frame.

## Static characteristics

The source-built capture client gained a metadata-only `--describe` mode. It
connects to CameraService, reads characteristics, and exits without opening a
sensor. The rear reports:

- AF modes off, auto, macro, continuous-video, and continuous-picture;
- flash present;
- 10.0-diopter minimum focus distance;
- 90-degree sensor orientation;
- fixed and variable ranges through 30 fps; and
- YUV sizes from 176×144 through 4128×3096.

The front reports AF off only, no flash, zero minimum-focus distance (fixed
focus), 270-degree orientation, the same frame-rate ranges, and YUV sizes
through 3264×2448.

## Autofocus

The rear still-template path initially used continuous-video AF and remained in
inactive state `0`. Continuous-picture is the matching mode for that template.
A 300-frame 1280×960 run then progressed from inactive (`0`) through passive
scan (`1`) to passive focused (`2`). AUTO white balance also progressed from
inactive to converged (`2`) during the longer run, correcting the earlier
first-frame-only observation. The front now requests AF off because its
characteristics identify a fixed-focus lens.

Rear result metadata reports `flash_state=2` (ready). No flash or torch request
was sent in this pass.

## Resolution tests

Direct rear capture delivered 60 and then 300 frames at 1280×960, with normal
session close and no boot change. The full color-filter, gamma, and PipeWire
path also supplied 300 1280×960 frames to a headless GStreamer consumer in
11.12 seconds.

GNOME Snapshot segfaulted after starting both 1280×960 and 960×720 sources.
Each launcher cleanup closed the ACamera session normally; neither failure
reset the tablet or left a PipeWire source behind. Snapshot remained stable at
720×480 for more than 1,100 frames. At that mode the color filter used 11.4% of
one CPU and under 1 MiB RSS; GStreamer used 3.1% CPU and about 21 MiB RSS.

The integrated preview is therefore 720×480 at 30 fps. Higher-resolution sensor
delivery is proven, but should be implemented as a separate still-capture path
or with a camera application that handles this synthetic PipeWire source more
robustly.
