

import glob
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk


HERE = os.path.dirname(os.path.abspath(__file__))
THIS_FILE = os.path.basename(__file__)


def find_game_script():
    for name in ("number guessing .py", "number_guessing_.py", "number_guessing.py"):
        path = os.path.join(HERE, name)
        if os.path.exists(path):
            return path
    for path in glob.glob(os.path.join(HERE, "number*guess*.py")):
        if os.path.basename(path) != THIS_FILE:
            return path
    return None


SCRIPT = find_game_script()


BG = "#0f172a"
CARD = "#1e293b"
INPUT_BG = "#0b1220"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
ACCENT = "#6366f1"
ACCENT_HOVER = "#818cf8"
GREEN = "#34d399"
ORANGE = "#fb923c"
BLUE = "#60a5fa"
RED = "#f87171"
FONT = "Segoe UI" if sys.platform.startswith("win") else "Helvetica"


class FlatButton(tk.Label):
    """Label-based button so colors look the same on Windows/Mac/Linux."""

    def __init__(self, parent, text, command, bg=ACCENT, hover=ACCENT_HOVER):
        super().__init__(
            parent, text=text, bg=bg, fg="white", cursor="hand2",
            font=(FONT, 12, "bold"), padx=22, pady=10,
        )
        self._bg, self._hover, self._cmd, self._enabled = bg, hover, command, True
        self.bind("<Button-1>", lambda e: self._enabled and self._cmd())
        self.bind("<Enter>", lambda e: self._enabled and self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg if self._enabled else "#334155"))

    def set_enabled(self, on):
        self._enabled = on
        self.config(bg=self._bg if on else "#334155",
                    cursor="hand2" if on else "arrow")


class GameUI:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.out_q = queue.Queue()
        self.buffer = ""
        self.attempts = 0
        self.history = []
        self.game_over = False

        root.title("Number Guesser")
        root.configure(bg=BG)
        root.geometry("420x560")
        root.minsize(380, 520)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_widgets()

        if SCRIPT is None:
            self.set_status("😅 Can't find your game script.\nPut it next to this file.", RED)
            self.entry.config(state="disabled")
            self.guess_btn.set_enabled(False)
            return

        self.start_game()
        self.root.after(50, self.poll_output)

    
    def build_widgets(self):
        tk.Label(self.root, text="🎯 Number Guesser", bg=BG, fg=TEXT,
                 font=(FONT, 22, "bold")).pack(pady=(28, 2))
        tk.Label(self.root, text="I'm thinking of a number between 1 and 10",
                 bg=BG, fg=MUTED, font=(FONT, 11)).pack()

        card = tk.Frame(self.root, bg=CARD, padx=24, pady=24)
        card.pack(padx=28, pady=22, fill="x")

        self.status = tk.Label(card, text="Take your best shot 👇", bg=CARD, fg=TEXT,
                               font=(FONT, 16, "bold"), wraplength=320, justify="center",
                               height=2)
        self.status.pack()

        self.raw_msg = tk.Label(card, text="", bg=CARD, fg=MUTED, font=(FONT, 10, "italic"))
        self.raw_msg.pack(pady=(2, 14))

        self.entry = tk.Entry(card, font=(FONT, 28, "bold"), justify="center", width=4,
                              bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
                              relief="flat", highlightthickness=2,
                              highlightbackground="#334155", highlightcolor=ACCENT)
        self.entry.pack(ipady=8)
        self.entry.bind("<Return>", lambda e: self.submit_guess())
        self.entry.focus_set()

        self.guess_btn = FlatButton(card, "Guess", self.submit_guess)
        self.guess_btn.pack(pady=(16, 0), fill="x")

        self.attempts_lbl = tk.Label(self.root, text="Attempts: 0", bg=BG, fg=TEXT,
                                     font=(FONT, 12, "bold"))
        self.attempts_lbl.pack()

        self.history_lbl = tk.Label(self.root, text="", bg=BG, fg=MUTED, font=(FONT, 11),
                                    wraplength=360, justify="center")
        self.history_lbl.pack(pady=(6, 10))

        self.again_btn = FlatButton(self.root, "Play again 🔄", self.start_game,
                                    bg=GREEN, hover="#6ee7b7")

   
    def start_game(self):
        script = SCRIPT
        python = sys.executable
        if script is None or python is None:
            return

        self.kill_proc()
        self.out_q = queue.Queue()
        self.buffer = ""
        self.attempts = 0
        self.history = []
        self.game_over = False

        env = dict(os.environ, PYTHONUNBUFFERED="1")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
        self.proc = subprocess.Popen(
            [python, "-u", script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, env=env, cwd=os.path.dirname(script), creationflags=flags,
        )
        threading.Thread(target=self.reader, args=(self.proc,), daemon=True).start()

        self.again_btn.pack_forget()
        self.set_status("Take your best shot 👇", TEXT)
        self.raw_msg.config(text="")
        self.attempts_lbl.config(text="Attempts: 0")
        self.history_lbl.config(text="")
        self.entry.config(state="normal")
        self.entry.delete(0, "end")
        self.entry.focus_set()
        self.guess_btn.set_enabled(True)

    def reader(self, proc):
        fd = proc.stdout.fileno()
        while True:
            try:
                chunk = os.read(fd, 1024)
            except OSError:
                break
            if not chunk:
                break
            self.out_q.put(chunk.decode(errors="replace"))

    def poll_output(self):
        try:
            while True:
                self.buffer += self.out_q.get_nowait()
        except queue.Empty:
            pass

        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:
                self.handle_line(line)

        self.root.after(50, self.poll_output)

    def handle_line(self, line):

        while line.lower().startswith("guess a number") and ": " in line:
            line = line.split(": ", 1)[1].strip()
        if not line:
            return
        self.raw_msg.config(text=f"“{line}”")
        low = line.lower()
        last = self.history[-1][0] if self.history else "?"
        if low.startswith("too low"):
            self.history[-1:] = [(last, "⬆")] if self.history else []
            self.set_status("📉 Too low!\nGo higher", BLUE)
        elif low.startswith("too high"):
            self.history[-1:] = [(last, "⬇")] if self.history else []
            self.set_status("📈 Too high!\nGo lower", ORANGE)
        elif low.startswith("congrat"):
            self.history[-1:] = [(last, "✅")] if self.history else []
            self.finish()
        elif "traceback" in low or "error" in low:
            self.set_status("💥 The game script hit an error", RED)
        self.refresh_history()

   
    def submit_guess(self):
        if self.game_over or not self.proc or self.proc.poll() is not None:
            return
        stdin = self.proc.stdin
        if stdin is None:
            return
        raw = self.entry.get().strip()
        if not raw.isdigit() or not (1 <= int(raw) <= 10):
            self.set_status("Pick a whole number\nfrom 1 to 10 🙂", RED)
            self.entry.select_range(0, "end")
            return

        guess = int(raw)
        self.attempts += 1
        self.attempts_lbl.config(text=f"Attempts: {self.attempts}")
        self.history.append((guess, "…"))
        self.refresh_history()
        try:
            stdin.write(f"{guess}\n".encode())
            stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        self.entry.delete(0, "end")

    def finish(self):
        self.game_over = True
        word = "attempt" if self.attempts == 1 else "attempts"
        self.set_status(f"🎉 You got it in\n{self.attempts} {word}!", GREEN)
        self.entry.config(state="disabled")
        self.guess_btn.set_enabled(False)
        self.again_btn.pack(pady=6)

    
    def set_status(self, text, color):
        self.status.config(text=text, fg=color)

    def refresh_history(self):
        self.history_lbl.config(text="   ".join(f"{g} {m}" for g, m in self.history))

    def kill_proc(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()

    def on_close(self):
        self.kill_proc()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    GameUI(root)
    root.mainloop()
