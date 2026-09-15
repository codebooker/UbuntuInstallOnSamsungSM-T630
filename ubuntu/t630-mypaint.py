#!/usr/bin/python3
"""Experimental MyPaint 2.0.1 Wayland UI adaptation, scoped to this app.

Use existing dockable brush/color panels instead of its broken chooser-popup
input grabs. No device injection, package-file patch, or user preference reset.
"""
import os
import runpy
import subprocess
import sys


def panel_popup(chooser, *args, **kwargs):
    kind = type(chooser).__name__
    if kind == 'BrushChooserPopup':
        group = chooser._chooser.groups_sb.get_value()
        tool, params = 'MyPaintBrushGroupTool', (group,)
    elif kind == 'ColorChooserPopup':
        tool, params = 'MyPaintHSVWheelTool', ()
    else:
        raise RuntimeError('Unsupported MyPaint chooser; refusing popup grab.')
    # reveal_tool_widget is idempotent and uses normal workspace/sidebar UI.
    return chooser.app.workspace.reveal_tool_widget(tool, params)


def main():
    if os.getuid() == 0 or os.environ.get('WAYLAND_DISPLAY') != 't630-gnome-0':
        raise SystemExit('Launch through the normal tablet GNOME pen-app helper.')
    version = subprocess.check_output(['/usr/bin/dpkg-query', '-W',
        '-f=${Version}', 'mypaint'], text=True).strip()
    if version != '2.0.1-10build2':
        raise SystemExit('MyPaint UI adaptation is validated only for 2.0.1-10build2.')
    os.environ['OMP_NUM_THREADS'] = '1'
    sys.path.insert(0, '/usr/lib/mypaint')
    from gui.windowing import ChooserPopup
    ChooserPopup.popup = panel_popup
    print('T630 MyPaint: brush/color quick choosers use dockable panels.', flush=True)
    runpy.run_path('/usr/bin/mypaint', run_name='__main__')


if __name__ == '__main__':
    main()
