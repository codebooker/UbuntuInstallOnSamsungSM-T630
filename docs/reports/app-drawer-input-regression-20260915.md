# App drawer and input regression — 2026-09-15

After a clean GNOME session restart, the owner could log in and adjust screen
brightness, but reported losing finger and S Pen click responsiveness when
opening the app menu. Pen cursor movement and its disappearance on finger
contact had previously continued. Do not infer that all physical events reached
GNOME correctly from the outer cursor alone.

The affected Shell still answered its control bus. ScreenSaver was inactive,
the panel was not blanked, and the existing Tablet Controls extension had no
reported extension error. The live screen showed the window-picker Activities
view, not the app grid. No new app-grid JavaScript exception appeared in the
bounded log check. Virtual input devices were enabled. These observations do
not establish that GNOME's event dispatch was healthy.

An unfinished overview animation or extra modal grab was considered, not
assigned as the cause. GNOME's overview uses a cover pane during transitions
and a modal grab; see the exact upstream
[GNOME 46 overview implementation](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/overview.js)
and [modal stack implementation](https://github.com/GNOME/gnome-shell/blob/46.0/js/ui/main.js).
Owner animations were already disabled; the diagnostic setting request left
that existing false value unchanged.

## Bounded instrumented replay

Added the source-only manual instrument in `tools/gnome-input-diagnostic/`.
It counts only touch/button event types while unlocked and samples overview,
cover-pane, and modal state every three seconds for at most 180 seconds. It
propagates every event unchanged, never changes grabs or authentication, and
does not log keys, coordinates, text, titles, or passwords. It is deliberately
not in any release package or owner-assets startup installer.

Started another normal software-rendered managed GNOME session, stopping only
the exact old managed desktop tree. Weston, hardware services, SSH, kernel,
boot image, and partitions were left running/unchanged. The normal startup
password lock verified. The temporary diagnostic loaded with no extension error.

During the physical replay, the samples showed:

- Normal window-picker state, then app-grid state with Show Apps checked.
- Overview animation inactive and cover pane hidden throughout those samples.
- One normal stage modal grab while the overview was open, and no modal stack
  after it closed. No extra grab appeared in these samples.
- Button presses and releases reaching Shell, grid opening/closing, and app-grid
  page changes visible in the screen viewer.

The owner confirmed, “It seems to be working now.” Touch begin/end counters
remained zero during this capture; button counts alone do not identify which
physical input produced them or prove the full direct-multitouch path works.
A final press/release count imbalance was not assigned as a stuck button:
the virtual devices subsequently reported all queried buttons released, and
stage capture need not observe every release consumed elsewhere.

Disabled the diagnostic normally and verified it reported disabled, with no
extension error. The owner then confirmed input kept working through repeated
drawer opening/closing with both finger and S Pen after observer removal.
This was a successful replay after session replacement, not a reproducible
root-cause fix. Leave the input regression open for repeated ordinary-session,
rotation, lock/unlock, and restart acceptance; do not install a blind device
reset or compositor restart loop.

All 268 tests completed (264 passes, four skips). The new JavaScript harness
checks unchanged event propagation, key exclusion, no locked-session counts,
bounded timer termination, and observer/timer cleanup on disable. Syntax checks
passed. No device-driver or released package contents changed in this follow-up.
