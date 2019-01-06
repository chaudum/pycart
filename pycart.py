"""
PyCart is an audio cart machine written in Python using Tcl/Tk as
cross-platform graphical interface. It provides a simple interface to load
samples into 9 pads with than can be played back in any order.
"""

import sndhdr
import time
import tkinter as tk
import uuid
import wave
from datetime import datetime
from pathlib import Path
from threading import Thread
from tkinter import messagebox, ttk
from tkinter.filedialog import askopenfilename
from typing import Callable, Dict, Mapping

import simpleaudio as sa
import toml


def load_conf(filename: str) -> Dict:
    with open(filename, "rb") as fp:
        return toml.loads(fp.read().decode("utf=8"))


def dump_conf() -> None:
    pass


class PyCartError(Exception):
    pass


class PyCartPad(tk.Frame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent)
        self.progress = ttk.Progressbar(self, orient=tk.HORIZONTAL)
        self.progress.pack(side=tk.BOTTOM)
        self.btn = PyCartButton(self, **kwargs)
        self.btn.pack(side=tk.BOTTOM)

    def restore(self, fname):
        self.btn.do_load(fname)


class PyCartButton(tk.Button):
    def __init__(self, *args, id=0, **kwargs) -> None:
        kwargs.update({"text": str(id), "command": self.on_click})
        super().__init__(*args, **kwargs)
        self._id = id
        self._file = None
        self._default_bg = self.cget("bg")

        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Load", command=self.load)
        self.menu.add_command(label="Play", command=self.play)
        self.menu.add_command(label="Loop", command=self.loop)
        self.menu.add_command(label="Reset", command=self.reset)
        self.bind("<Button-3>", self.on_right_click)

    def on_click(self, *args, **kwargs):
        if self.cget("state") == tk.DISABLED:
            return
        self.play()

    def on_right_click(self, e):
        self.menu.post(e.x_root, e.y_root)

    def load(self):
        """
        Assign audio file to button
        """
        fname = askopenfilename(
            initialdir=Path.home(),
            filetypes=(("Wave files", ".wav"), ("All files", "*")),
        )
        if fname:
            self.do_load(fname)

    def do_load(self, fname):
        try:
            self._file = PyCartAudio(fname, self._on_start, self._on_stop)
        except PyCartError as e:
            messagebox.showerror("Error", str(e))
        else:
            self.config(text=Path(fname).name, bg="green")

    def play(self):
        """
        Play assigned audio file
        """
        if self._file:
            print(f"Play {self._file}")
            self._file.start()

    def loop(self):
        pass

    def reset(self):
        """
        Unassign audio file from button
        """
        self._file = None
        self.config(text=self._id, bg=self._default_bg)

    def _on_start(self, sender):
        self.config(state=tk.DISABLED, bg="red")

    def _on_stop(self, sender):
        self.config(state=tk.NORMAL, bg="green")


class PyCartAudio:
    def __init__(self, fname: str, on_start: Callable, on_stop: Callable) -> None:
        super().__init__()
        self.info = sndhdr.whathdr(fname)
        if not self.info:
            raise PyCartError(f"Could not load file {fname}. Not a valid audio file.")
        self.wav = sa.WaveObject.from_wave_file(fname)
        self.start_callback = on_start
        self.stop_callback = on_stop
        self.file = Path(fname)

    def __str__(self):
        return f"<{self.file} {self.info}>"

    def start(self):
        self.audio = Thread(target=self.run)
        self.audio.start()

    def run(self):
        self.start_callback(self)
        play_obj = self.wav.play()
        play_obj.wait_done()
        self.stop_callback(self)


class Clock(Thread):
    def __init__(self) -> None:
        super().__init__()
        self.enabled = True
        self.callbacks: Dict[str, Callable] = {}

    def add_callback(self, name: str, callback: Callable):
        self.callbacks[name] = callback

    def remove_callback(self, name):
        del self.callbacks[name]

    def run(self):
        while self.enabled:
            now = datetime.now()
            sec_remaining = (60 - now.second) % 60
            min_remaining = (60 + (60 - now.second) // 60) - now.minute - 1
            for cb in self.callbacks.values():
                cb(
                    current_time=now.strftime("%H:%M:%S"),
                    remaining=f"-{min_remaining:02}:{sec_remaining:02}",
                )
            time.sleep(0.25)

    def stop(self):
        self.enabled = False
        self.join()


class PyCart(tk.Frame):
    def __init__(self, root):
        super().__init__(master=root)
        self.pack()
        self.clock = Clock()
        self.clock.start()
        self.pads = []
        self.create_menu()
        self.create_widgets()
        self.create_clock()
        self.bind("<Key>", self.on_key)

    def create_menu(self):
        menubar = tk.Menu(self.master)
        file_menu = tk.Menu(menubar)
        file_menu.add_command(label="Open", command=self.open)
        file_menu.add_command(label="Save", command=self.save)
        file_menu.add_command(label="Quit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        display_menu = tk.Menu(menubar)
        display_menu.add_command(label="Clock", command=self.show_clock)
        menubar.add_cascade(label="Display", menu=display_menu)
        self.master.config(menu=menubar)

    def create_widgets(self):
        btn_id = 1
        for x in range(3):
            for y in range(3):
                btn = PyCartButton(self, width=32, height=5, id=btn_id)
                btn.grid(row=x, column=y, padx=5, pady=5)
                self.pads.append(btn)
                btn_id += 1

    def create_clock(self):
        clock_label = tk.Label(self, text="--:--:--")
        clock_label.grid(row=3, column=0, padx=5, pady=5, columnspan=2)
        remain_label = tk.Label(self, text="--:--")
        remain_label.grid(row=3, column=2, padx=5, pady=5, columnspan=1)

        def update(current_time, remaining):
            clock_label.config(text=current_time)
            remain_label.config(text=remaining)

        self.clock.add_callback("mini", update)

    def open(self):
        fname = askopenfilename(
            initialdir=Path.home(),
            filetypes=(("TOML files", ".toml"), ("All files", "*")),
        )
        if fname:
            conf = load_conf(fname)
            for idx, pad in enumerate(conf["pads"]):
                self.pads[idx].do_load(pad["file"])

    def save(self):
        pass

    def show_clock(self):
        clock_id = uuid.uuid4().hex
        top = tk.Toplevel(self)
        top.title("Studio Clock")

        def close():
            top.destroy()
            self.clock.remove_callback(clock_id)

        clock_label = tk.Label(top, text="--:--:--", fg="green", font=("monospace", 96))
        clock_label.pack()
        remain_label = tk.Label(top, text="--:--", fg="red", font=("monospace", 96))
        remain_label.pack()

        button = tk.Button(top, text="Close", command=close)
        button.pack(side=tk.BOTTOM)

        def update(current_time, remaining):
            clock_label.config(text=current_time)
            remain_label.config(text=remaining)

        self.clock.add_callback(clock_id, update)

    def on_key(self, e):
        try:
            idx = int(e.char) - 1
        except ValueError as ex:
            pass
        else:
            if idx >= 0:
                self.pads[idx].on_click(e)
            return

        if e.char.lower() == "q":
            self.quit()

    def quit(self):
        self.clock.stop()
        sa.stop_all()
        self.master.destroy()


def main():
    root = tk.Tk()
    app = PyCart(root)
    app.focus_set()
    app.mainloop()
