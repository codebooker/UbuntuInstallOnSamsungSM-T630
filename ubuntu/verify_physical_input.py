#!/usr/bin/python3
"""On-device physical verification. No synthetic injection or keyboard capture."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import json
import math
import os
from pathlib import Path
import time
import uuid

result = {'test_id':str(uuid.uuid4()), 'pid':os.getpid(),
          'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
          'finger':False, 'pen_click':False, 'pen_drag':False,
          'complete':False, 'closed':False, 'synthetic_input_used':False}
target = Path('/run/t630-physical-input-result.json')
def save():
    result['updated_monotonic'] = round(time.monotonic(),3)
    target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)

class Verify(Gtk.Window):
    def __init__(self):
        super().__init__(title='Ubuntu — final input check')
        self.set_decorated(False)
        self.fullscreen()
        self.connect('destroy', self.closed)
        self.fixed = Gtk.Fixed()
        self.add(self.fixed)
        self.heading = Gtk.Label()
        self.heading.set_markup('<span size="30000" weight="bold">Ubuntu is installed. Two quick checks.</span>')
        self.fixed.put(self.heading,70,70)
        self.status = Gtk.Label(label='Tap the first box with your finger. Then drag the pen box into the outlined area.')
        self.fixed.put(self.status,70,140)
        self.finger = Gtk.EventBox()
        self.finger.set_name('finger-target')
        self.finger_label = Gtk.Label(label='1. Tap here with your FINGER')
        self.finger.add(self.finger_label)
        self.finger.set_size_request(430,150)
        self.finger.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.TOUCH_MASK)
        self.finger.connect('button-press-event',self.finger_event)
        self.finger.connect('touch-event',self.finger_event)
        self.fixed.put(self.finger,280,280)
        self.zone = Gtk.Frame(label='Drop the pen box here')
        self.zone.set_size_request(460,190)
        self.fixed.put(self.zone,1060,650)
        self.pen = Gtk.EventBox()
        self.pen.set_name('pen-target')
        self.pen_label = Gtk.Label(label='2. Drag this with the S PEN →')
        self.pen.add(self.pen_label)
        self.pen.set_size_request(390,150)
        self.pen.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.pen.connect('button-press-event',self.pen_down)
        self.pen.connect('motion-notify-event',self.pen_move)
        self.pen.connect('button-release-event',self.pen_up)
        self.fixed.put(self.pen,280,670)
        self.drag = None
        self.pen_position=(280,670)
        close = Gtk.Button(label='Close test')
        close.connect('clicked',lambda *_: self.destroy())
        self.fixed.put(close,70,1010)
        css=Gtk.CssProvider()
        css.load_from_data(b'window { background:#2c1640; color:white; } label,button { font-size:23px; } #finger-target,#pen-target { background:#563b83; border:3px solid #bca4e6; border-radius:10px; } frame { border:3px dashed #c9b3ee; }')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        save()

    def source(self,e):
        d=e.get_source_device()
        return d.get_source() if d else None

    def finger_event(self,widget,e):
        if self.source(e)==Gdk.InputSource.TOUCHSCREEN and e.type in (Gdk.EventType.BUTTON_PRESS,Gdk.EventType.TOUCH_BEGIN):
            result['finger']=True
            self.finger_label.set_text('Finger touch: PASS ✓')
            save(); self.check()
        return True

    def pen_down(self,widget,e):
        if self.source(e)!=Gdk.InputSource.PEN or e.button!=1:
            return True
        result['pen_click']=True
        self.drag=(e.x_root,e.y_root,*self.pen_position)
        self.max_distance=0.0
        self.status.set_text('Keep the pen tip down and move the box into the outlined area.')
        save()
        return True

    def pen_move(self,widget,e):
        if self.drag is None or self.source(e)!=Gdk.InputSource.PEN:
            return True
        sx,sy,px,py=self.drag
        dx,dy=e.x_root-sx,e.y_root-sy
        self.max_distance=max(self.max_distance,math.hypot(dx,dy))
        self.pen_position=(int(px+dx),int(py+dy))
        self.fixed.move(self.pen,*self.pen_position)
        return True

    def pen_up(self,widget,e):
        if self.drag is None or self.source(e)!=Gdk.InputSource.PEN:
            return True
        self.drag=None
        x,y=self.pen_position
        if self.max_distance>100 and 1060<=x+195<=1520 and 650<=y+75<=840:
            result['pen_drag']=True
            result['pen_drag_distance']=round(self.max_distance,1)
            self.pen_label.set_text('S Pen click + drag: PASS ✓')
        else:
            self.pen_position=(280,670)
            self.fixed.move(self.pen,*self.pen_position)
            self.status.set_text('Try again: keep the tip down until the pen box reaches the outlined area.')
        save(); self.check()
        return True

    def check(self):
        if result['finger'] and result['pen_click'] and result['pen_drag']:
            result['complete']=True
            self.heading.set_markup('<span size="30000" weight="bold">Both physical input checks passed ✓</span>')
            self.status.set_text('The result is recorded. Returning to the desktop…')
            save()
            GLib.timeout_add_seconds(3,lambda:(self.destroy(),False)[1])

    def closed(self,*_):
        result['closed']=True
        save()
        Gtk.main_quit()

app=Verify()
app.show_all()
Gtk.main()
