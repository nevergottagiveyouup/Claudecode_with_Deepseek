import tkinter as tk
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import (
    load_config, save_config, get_api_key, CONFIG_FILE
)

# Ensure dummy config for screenshot
if not os.path.exists(CONFIG_FILE):
    save_config({"api_key": "sk-demo-key-for-screenshot"})

class SettingsShot:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DeepSeek Proxy")
        self.root.geometry("300x390")

        # replica of _open_settings
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("380x200")
        dlg.resizable(False, False)

        tk.Label(dlg, text="DeepSeek API Key:", font=("Segoe UI", 10)).pack(pady=(16, 4))
        key_frame = tk.Frame(dlg)
        key_frame.pack(pady=(0, 8))
        key_var = tk.StringVar(value=get_api_key())
        self._key_entry = tk.Entry(key_frame, textvariable=key_var, show="*",
                                   font=("Consolas", 10), width=36)
        self._key_entry.pack(side=tk.LEFT, padx=(0, 2))
        show_var = tk.BooleanVar(value=False)

        def toggle_show():
            self._key_entry.config(show="" if show_var.get() else "*")

        tk.Checkbutton(key_frame, text="Show", variable=show_var, command=toggle_show,
                       font=("Segoe UI", 8)).pack(side=tk.LEFT)

        status = tk.Label(dlg, text="", font=("Segoe UI", 9), fg="gray")
        status.pack(pady=(2, 6))

        def do_save():
            status.config(text="Saved successfully", fg="#2e7d32")

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=(0, 12))
        tk.Button(btn_frame, text="Save", font=("Segoe UI", 10), width=10,
                  command=do_save).pack()

        self.root.withdraw()
        dlg.after(300, lambda: sys.exit(0))
        dlg.mainloop()

if __name__ == "__main__":
    SettingsShot()
