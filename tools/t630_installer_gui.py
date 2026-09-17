#!/usr/bin/env python3
"""Button-driven host interface for the guarded SM-T630 installer."""

from __future__ import annotations

from pathlib import Path
import os
import queue
import subprocess
import sys
import threading
from typing import List, Optional, Tuple


COORDINATOR = Path(__file__).with_name("t630_installer.py").resolve()
ERASE_PHRASE = "ERASE SM-T630 LINUXROOT"


def command_for(
        source: str, path: str, action: str, acknowledged: bool
) -> Tuple[List[str], Optional[str]]:
    if source not in {"host", "tablet", "staged"}:
        raise ValueError("Select where the installer bundle is located.")
    if action not in {"verify", "stage", "prepare", "install"}:
        raise ValueError("Unknown installer action.")
    if source != "staged" and not path.strip():
        raise ValueError("Select or enter the sealed bundle path.")

    command = [sys.executable, str(COORDINATOR)]
    if source == "host":
        command += ["--host-bundle", path.strip()]
    elif source == "tablet":
        command += ["--tablet-bundle", path.strip()]
    else:
        command += ["--staged"]

    if action == "verify":
        if source != "host":
            raise ValueError("Verify only is available for a bundle on this computer.")
        command += ["--verify-only"]
    elif action == "stage":
        if source == "staged":
            raise ValueError("The bundle is already staged in tablet RAM.")
    elif action == "prepare":
        if source == "host":
            raise ValueError(
                "A host bundle must be staged from the maintenance environment; "
                "use Stage, then select Already staged and Prepare if needed.")
        command += ["--prepare"]
    else:
        if not acknowledged:
            raise ValueError(
                "Confirm that the exact stock recovery package is retained and deeply verified.")
        command += ["--install", "--acknowledge-stock-recovery"]
        return command, ERASE_PHRASE + "\n"
    return command, None


class InstallerGUI:
    def __init__(self, root, tk, ttk, filedialog, messagebox):
        self.root = root
        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.events: queue.Queue = queue.Queue()
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.buttons = []

        root.title("Ubuntu for Samsung SM-T630")
        root.geometry("760x610")
        root.minsize(680, 520)
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.source = tk.StringVar(value="host")
        self.path = tk.StringVar(value="")
        self.acknowledged = tk.BooleanVar(value=False)
        self.erase = tk.StringVar(value="")
        self.status = tk.StringVar(value="Ready — no action has been taken")

        outer = ttk.Frame(root, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Install Ubuntu on SM-T630",
                  font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("This interface uses the same hash, geometry, power, recovery, "
                  "and typed-authorization gates as the accepted command-line workflow."),
            wraplength=710).pack(anchor="w", pady=(4, 16))

        source_frame = ttk.LabelFrame(outer, text="Installer bundle", padding=10)
        source_frame.pack(fill="x")
        for label, value in (
            ("On this computer", "host"),
            ("On the tablet's Ubuntu partition", "tablet"),
            ("Already staged in tablet RAM", "staged"),
        ):
            ttk.Radiobutton(
                source_frame, text=label, value=value, variable=self.source,
                command=self.source_changed).pack(anchor="w")
        path_row = ttk.Frame(source_frame)
        path_row.pack(fill="x", pady=(8, 0))
        self.path_entry = ttk.Entry(path_row, textvariable=self.path)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(path_row, text="Browse…", command=self.browse)
        self.browse_button.pack(side="left", padx=(8, 0))

        action_frame = ttk.LabelFrame(outer, text="Action", padding=10)
        action_frame.pack(fill="x", pady=(12, 0))
        button_row = ttk.Frame(action_frame)
        button_row.pack(fill="x")
        for label, action in (
            ("Verify", "verify"), ("Stage", "stage"),
            ("Prepare (read-only)", "prepare"), ("Install Ubuntu", "install"),
        ):
            button = ttk.Button(
                button_row, text=label,
                command=lambda selected=action: self.start(selected))
            button.pack(side="left", padx=(0, 8))
            self.buttons.append(button)

        ttk.Checkbutton(
            action_frame,
            text="I retained and deeply verified the exact DZE3/XAR stock package",
            variable=self.acknowledged).pack(anchor="w", pady=(12, 0))
        phrase_row = ttk.Frame(action_frame)
        phrase_row.pack(fill="x", pady=(8, 0))
        ttk.Label(phrase_row, text="For Install, type:").pack(side="left")
        ttk.Label(phrase_row, text=ERASE_PHRASE,
                  font=("TkDefaultFont", 10, "bold")).pack(side="left", padx=(5, 12))
        ttk.Entry(phrase_row, textvariable=self.erase, show="").pack(
            side="left", fill="x", expand=True)

        ttk.Label(outer, textvariable=self.status).pack(anchor="w", pady=(12, 4))
        self.log = tk.Text(outer, height=14, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True)
        self.source_changed()
        root.after(100, self.drain_events)

    def source_changed(self):
        staged = self.source.get() == "staged"
        self.path_entry.configure(state="disabled" if staged else "normal")
        self.browse_button.configure(
            state="normal" if self.source.get() == "host" else "disabled")

    def browse(self):
        selected = self.filedialog.askdirectory(title="Select sealed installer bundle")
        if selected:
            self.path.set(selected)

    def append(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self, action: str):
        if self.running:
            return
        if action == "install" and self.erase.get() != ERASE_PHRASE:
            self.messagebox.showerror(
                "Install refused", "The erase phrase does not match. Nothing was changed.")
            return
        try:
            command, stdin_text = command_for(
                self.source.get(), self.path.get(), action,
                self.acknowledged.get())
        except ValueError as error:
            self.messagebox.showerror("Action refused", str(error))
            return
        if action == "install" and not self.messagebox.askyesno(
                "Final destructive confirmation",
                "This will permanently erase only the 64 GiB Ubuntu linuxroot.\n\n"
                "Android userdata is separately guarded. Continue?"):
            return
        self.status.set(f"Running {action}…")
        self.running = True
        self.append("\n$ " + " ".join(command) + "\n")
        for button in self.buttons:
            button.configure(state="disabled")
        threading.Thread(
            target=self.worker, args=(command, stdin_text, action), daemon=True).start()

    def worker(self, command: List[str], stdin_text: Optional[str], action: str):
        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if stdin_text is not None:
                assert self.process.stdin is not None
                self.process.stdin.write(stdin_text)
                self.process.stdin.close()
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.events.put(("output", line))
            result = self.process.wait()
            self.events.put(("done", action, result))
        except Exception as error:
            self.events.put(("error", str(error)))

    def drain_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "output":
                    self.append(event[1])
                elif event[0] == "done":
                    _, action, result = event
                    self.process = None
                    self.running = False
                    if result == 0:
                        self.status.set(f"{action.capitalize()} completed successfully")
                        if action in {"stage", "prepare"}:
                            self.source.set("staged")
                            self.source_changed()
                    else:
                        self.status.set(f"{action.capitalize()} refused or failed (status {result})")
                    for button in self.buttons:
                        button.configure(state="normal")
                else:
                    self.process = None
                    self.running = False
                    self.status.set("Installer process could not start")
                    self.messagebox.showerror("Installer error", event[1])
                    for button in self.buttons:
                        button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(100, self.drain_events)

    def close(self):
        if self.running:
            self.messagebox.showwarning(
                "Installer is running",
                "Wait for the current guarded phase to finish before closing this window.")
            return
        self.root.destroy()


def main() -> None:
    os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except ImportError as error:
        raise SystemExit("Python Tk support is required for the installer GUI") from error
    root = tk.Tk()
    InstallerGUI(root, tk, ttk, filedialog, messagebox)
    root.mainloop()


if __name__ == "__main__":
    main()
