#!/usr/bin/python3
"""On-tablet password setup. Secrets go only to chpasswd stdin, never logs/argv."""
import ctypes
import subprocess
import threading
import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, GLib

class PasswordWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title='Set your tablet password')
        self.set_default_size(880, 460)
        self.set_border_width(28)
        self.connect('destroy', Gtk.main_quit)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=18)
        self.add(box)
        description=Gtk.Label(label='Choose a local password for the tablet account.\nUse it with sudo to install apps. SSH password login stays disabled.',xalign=0)
        description.set_line_wrap(True)
        box.pack_start(description,False,False,0)
        self.first=Gtk.Entry();self.second=Gtk.Entry()
        for entry,label in [(self.first,'New password (at least 8 characters)'),(self.second,'Repeat password')]:
            entry.set_visibility(False)
            entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            entry.set_placeholder_text(label)
            box.pack_start(entry,False,False,0)
        self.status=Gtk.Label(label='Enter the password on the tablet, not in chat.',xalign=0)
        self.status.set_line_wrap(True)
        box.pack_start(self.status,False,False,0)
        self.button=Gtk.Button(label='Save password and enable sudo')
        self.button.set_size_request(-1,64)
        self.button.connect('clicked',self.save)
        box.pack_start(self.button,False,False,0)

    def save(self,_):
        secret=self.first.get_text()
        if len(secret)<8 or '\n' in secret or '\r' in secret:
            self.status.set_text('Use at least 8 characters, without line breaks.');return
        if secret!=self.second.get_text():
            self.status.set_text('The two passwords do not match.');return
        self.button.set_sensitive(False)
        self.first.set_sensitive(False);self.second.set_sensitive(False)
        self.status.set_text('Saving locally…')
        def worker():
            password_saved=False
            try:
                subprocess.run(['/usr/sbin/chpasswd'],input='tablet:'+secret+'\n',text=True,
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                               timeout=15,check=True)
                password_saved=True
                subprocess.run(['/usr/sbin/usermod','-aG','sudo','tablet'],
                               stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                               timeout=15,check=True)
                success=True
            except (OSError,subprocess.SubprocessError):
                success=False
            GLib.idle_add(self.finished,success,password_saved)
        threading.Thread(target=worker,daemon=True).start()

    def finished(self,success,password_saved):
        self.first.set_text('');self.second.set_text('')
        if success:
            self.status.set_text('Password saved. Open a NEW Terminal window, then use sudo.\nYou can close this window now.')
            self.button.set_label('Done')
            self.button.set_sensitive(True)
            self.button.disconnect_by_func(self.save)
            self.button.connect('clicked',lambda _:self.destroy())
        else:
            self.status.set_text('Password saved, but sudo setup needs attention. You can retry.' if password_saved else 'Could not save the password. Please try again.')
            self.button.set_sensitive(True)
            self.first.set_sensitive(True);self.second.set_sensitive(True)
        return False

ctypes.CDLL(None).prctl(15,b't630-password',0,0,0)
window=PasswordWindow()
window.show_all()
window.first.grab_focus()
Gtk.main()
