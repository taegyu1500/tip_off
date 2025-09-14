from __future__ import annotations
import tkinter as tk

class AttentionManager:
    def __init__(self, root: tk.Tk, topmost_default: bool, bump_ms: int, topmost_on_notify: bool):
        self.root = root
        self.topmost_default = bool(topmost_default)
        self.bump_ms = int(bump_ms)
        self.topmost_on_notify = bool(topmost_on_notify)
        try:
            self.root.wm_attributes("-topmost", self.topmost_default)
        except Exception:
            pass

    def bump(self):
        if not self.topmost_on_notify:
            return
        try:
            self.root.lift()
            self.root.wm_attributes("-topmost", True)
            self.root.after(self.bump_ms, self._restore)
        except Exception:
            pass

    def _restore(self):
        try:
            self.root.wm_attributes("-topmost", self.topmost_default)
        except Exception:
            pass
