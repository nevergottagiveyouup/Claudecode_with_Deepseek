import tkinter as tk
import subprocess
import os
import time
import sys
import json
import winreg
import threading
import atexit

LITELLM_PATH = r"C:\Users\34967\AppData\Roaming\Python\Python313\Scripts\litellm.exe"
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "litellm_config.yaml")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
MASTER_KEY = "sk-litellm-master-key"
DS_ANTHROPIC_URL = "https://api.deepseek.com/anthropic"
LOCAL_URL = "http://localhost:4000"
REG_PATH = r"Environment"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}


def save_config(cfg):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)


def get_api_key():
    cfg = load_config()
    return cfg.get("api_key", "") or os.environ.get("DEEPSEEK_API_KEY", "")

PROXY_MODELS = {
    "V4 Flash (Fast)":   {"ds": "deepseek/deepseek-v4-flash",   "cc": "claude-sonnet-4-6"},
    "V4 Pro (Powerful)": {"ds": "deepseek/deepseek-v4-pro",     "cc": "claude-opus-4-6"},
}

DIRECT_MODELS = {
    "V4 Flash (Fast)":        "deepseek-v4-flash",
    "V4 Pro (Powerful)":      "deepseek-v4-pro",
    "V4 Flash + Think (R1)":  "deepseek-v4-flash",
}


def _stop_proxy():
    subprocess.run(['taskkill', '/f', '/t', '/im', 'litellm.exe'],
                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        for line in r.stdout.splitlines():
            if ':4000' in line and 'LISTENING' in line:
                pid = line.strip().split()[-1]
                subprocess.run(['taskkill', '/f', '/pid', pid],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass


def is_proxy_running():
    try:
        r = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        return any(':4000' in l and 'LISTENING' in l for l in r.stdout.splitlines())
    except:
        return False


def set_direct_vars(model_id, thinking=False):
    for k, v in [("ANTHROPIC_BASE_URL", DS_ANTHROPIC_URL),
                 ("ANTHROPIC_AUTH_TOKEN", get_api_key()),
                 ("ANTHROPIC_MODEL", model_id)]:
        _set_reg(k, v)
    if thinking:
        _set_reg("CLAUDE_CODE_EFFORT_LEVEL", "max")
    else:
        _remove_reg("CLAUDE_CODE_EFFORT_LEVEL")
        subprocess.run('setx CLAUDE_CODE_EFFORT_LEVEL "" >nul 2>&1',
                       shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run('setx ANTHROPIC_DEFAULT_OPUS_MODEL "" >nul 2>&1',
                   shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    subprocess.run('setx ANTHROPIC_DEFAULT_SONNET_MODEL "" >nul 2>&1',
                   shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


def set_proxy_vars(cc_model):
    for k, v in [("ANTHROPIC_BASE_URL", LOCAL_URL),
                 ("ANTHROPIC_AUTH_TOKEN", MASTER_KEY),
                 ("ANTHROPIC_MODEL", cc_model)]:
        _set_reg(k, v)
    _remove_reg("CLAUDE_CODE_EFFORT_LEVEL")
    subprocess.run('setx CLAUDE_CODE_EFFORT_LEVEL "" >nul 2>&1',
                   shell=True, creationflags=subprocess.CREATE_NO_WINDOW)


def _set_reg(key, val):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as r:
            winreg.SetValueEx(r, key, 0, winreg.REG_SZ, val)
        subprocess.run(f'setx {key} "{val}" >nul 2>&1', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass


def _remove_reg(key):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as r:
            winreg.DeleteValue(r, key)
    except FileNotFoundError:
        pass


ALL_KEYS = ["ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL",
            "CLAUDE_CODE_EFFORT_LEVEL", "ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_DEFAULT_SONNET_MODEL"]


def write_litellm_config():
    api_key = get_api_key()
    with open(CONFIG, 'r') as f:
        content = f.read()
    content = content.replace("YOUR_DEEPSEEK_API_KEY", api_key)
    tmp = CONFIG + ".tmp"
    with open(tmp, 'w') as f:
        f.write(content)
    return tmp


def clear_all_vars():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as r:
            for k in ALL_KEYS:
                try:
                    winreg.DeleteValue(r, k)
                except FileNotFoundError:
                    pass
        for k in ALL_KEYS:
            subprocess.run(f'setx {k} "" >nul 2>&1', shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DeepSeek Proxy")
        self.root.geometry("300x370")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_exit)
        atexit.register(self._cleanup)

        self._on = False
        self._mode = "direct"

        # --- Mode selector ---
        tk.Label(self.root, text="Connection Mode:", font=("Segoe UI", 9)).pack(pady=(12, 2))
        mode_frame = tk.Frame(self.root)
        mode_frame.pack()
        self.mode_var = tk.StringVar(value="direct")
        rb1 = tk.Radiobutton(mode_frame, text="Direct (recommended)", variable=self.mode_var,
                             value="direct", font=("Segoe UI", 9), command=self._on_mode_change)
        rb1.pack(anchor="w")
        rb2 = tk.Radiobutton(mode_frame, text="Proxy (via LiteLLM)", variable=self.mode_var,
                             value="proxy", font=("Segoe UI", 9), command=self._on_mode_change)
        rb2.pack(anchor="w")

        # --- Status ---
        self.status_label = tk.Label(self.root, text="", font=("Segoe UI", 11, "bold"))
        self.status_label.pack(pady=(12, 4))
        self.info_label = tk.Label(self.root, text="", font=("Segoe UI", 9), fg="gray")
        self.info_label.pack()

        # --- Model selector ---
        sel_frame = tk.Frame(self.root)
        sel_frame.pack(pady=(6, 0))
        tk.Label(sel_frame, text="Model:", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        self.model_var = tk.StringVar()
        self.model_menu = tk.OptionMenu(sel_frame, self.model_var, "", command=self._on_model_change)
        self.model_menu.config(font=("Segoe UI", 9), width=20)
        self.model_menu.pack(side=tk.LEFT, padx=(4, 0))

        # --- Thinking checkbox (direct only) ---
        self.think_var = tk.BooleanVar(value=False)
        self.think_cb = tk.Checkbutton(self.root, text="Thinking mode (R1)", font=("Segoe UI", 9),
                                       variable=self.think_var, command=self._on_model_change)
        self.think_cb.pack(pady=(4, 0))

        # --- Toggle button ---
        self.btn = tk.Button(self.root, text="", font=("Segoe UI", 11),
                             width=16, height=1, command=self.toggle, state=tk.DISABLED)
        self.btn.pack(pady=14)

        # --- System Status ---
        status_frame = tk.LabelFrame(self.root, text="System Status", font=("Segoe UI", 8), padx=6, pady=4)
        status_frame.pack(fill="x", padx=12, pady=(0, 8))
        self.status_url = tk.Label(status_frame, text="URL:   -", font=("Consolas", 8), fg="#666", anchor="w", justify="left")
        self.status_url.pack(fill="x")
        self.status_model = tk.Label(status_frame, text="Model: -", font=("Consolas", 8), fg="#666", anchor="w", justify="left")
        self.status_model.pack(fill="x")
        self.status_extra = tk.Label(status_frame, text="Effort: -", font=("Consolas", 8), fg="#666", anchor="w", justify="left")
        self.status_extra.pack(fill="x")

        tk.Button(self.root, text="Settings", font=("Segoe UI", 8),
                  command=self._open_settings).pack(pady=(0, 4))

        self._on_mode_change()
        self.root.after(300, lambda: self.btn.config(state=tk.NORMAL))
        self.root.after(500, self._check_api_key)

    def _open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Settings")
        dlg.geometry("380x200")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

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
            key = key_var.get().strip()
            if not key:
                status.config(text="Key cannot be empty", fg="#c62828")
                return
            save_config({"api_key": key})
            status.config(text="Saved successfully", fg="#2e7d32")

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=(0, 12))
        tk.Button(btn_frame, text="Save", font=("Segoe UI", 10), width=10,
                  command=do_save).pack()

        dlg.wait_window()

    def _check_api_key(self):
        if not get_api_key():
            self._open_settings()

    def _on_mode_change(self, *args):
        was_on = self._on
        prev_mode = self._mode
        self._mode = self.mode_var.get()

        menu = self.model_menu
        menu['menu'].delete(0, 'end')
        if self._mode == "direct":
            self.think_cb.pack(pady=(4, 0))
            models = DIRECT_MODELS
            menu.config(width=22)
            for label in models:
                menu['menu'].add_command(label=label, command=tk._setit(self.model_var, label, self._on_model_change))
            self.model_var.set("V4 Flash (Fast)")
        else:
            self.think_cb.pack_forget()
            self.think_var.set(False)
            models = PROXY_MODELS
            menu.config(width=20)
            for label in models:
                menu['menu'].add_command(label=label, command=tk._setit(self.model_var, label, self._on_model_change))
            self.model_var.set("V4 Flash (Fast)")

        if was_on and prev_mode != self._mode:
            self.btn.config(state=tk.DISABLED, text="Switching...", bg="#999")
            def switch():
                if prev_mode == "proxy":
                    _stop_proxy()
                elif self._mode == "proxy":
                    self._start_litellm()
                    for _ in range(10):
                        time.sleep(0.2)
                        if is_proxy_running():
                            break
                self._apply_vars()
                self.root.after(0, self._refresh_ui)
            threading.Thread(target=switch, daemon=True).start()
        else:
            self._on_model_change()

    def _on_model_change(self, *args):
        if self._mode == "direct" and "Think" in self.model_var.get():
            self.think_var.set(True)
        elif "Think" not in self.model_var.get():
            self.think_var.set(False)
        if self._on:
            def apply_and_refresh():
                self._apply_vars()
                self.root.after(0, self._refresh_ui)
            threading.Thread(target=apply_and_refresh, daemon=True).start()
        else:
            self._refresh_ui()

    def _apply_vars(self):
        model = self.model_var.get()
        if self._mode == "direct":
            thinking = self.think_var.get()
            set_direct_vars(DIRECT_MODELS[model], thinking)
        else:
            set_proxy_vars(PROXY_MODELS[model]["cc"])

    def _get_reg_val(self, key):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as r:
                val, _ = winreg.QueryValueEx(r, key)
                return val
        except FileNotFoundError:
            return None

    def _refresh_ui(self):
        mode = self.mode_var.get()
        model = self.model_var.get()

        if self._on:
            label = f"Direct: {model}" if mode == "direct" else f"Proxy: {model}"
            self.status_label.config(text="ON", fg="#2e7d32")
            self.info_label.config(text=label)
            self.btn.config(text="Turn OFF", bg="#ef5350", fg="white",
                            activebackground="#c62828", state=tk.NORMAL)
        else:
            self.status_label.config(text="OFF", fg="#757575")
            self.info_label.config(text=f"{'Direct' if mode == 'direct' else 'Proxy'} - {model}")
            self.btn.config(text="Turn ON", bg="#43a047", fg="white",
                            activebackground="#2e7d32", state=tk.NORMAL)

        base = self._get_reg_val("ANTHROPIC_BASE_URL") or "-"
        mod = self._get_reg_val("ANTHROPIC_MODEL") or "-"
        effort = self._get_reg_val("CLAUDE_CODE_EFFORT_LEVEL")
        self.status_url.config(text=f"URL:   {base}")
        self.status_model.config(text=f"Model: {mod}")
        self.status_extra.config(text=f"Effort: {effort}" if effort else "Effort: -")

    def toggle(self):
        if self._on:
            self._do_off()
        else:
            self._do_on()

    def _do_on(self):
        self._on = True
        self.btn.config(state=tk.DISABLED, text="Starting...", bg="#999")
        self.status_label.config(fg="#e65100")

        def run():
            mode = self.mode_var.get()
            if mode == "proxy":
                self._start_litellm()
                for _ in range(15):
                    time.sleep(0.3)
                    if is_proxy_running():
                        break
            self._apply_vars()
            self.root.after(0, self._refresh_ui)

        threading.Thread(target=run, daemon=True).start()

    def _start_litellm(self):
        config_path = write_litellm_config()
        env = os.environ.copy()
        env['DEEPSEEK_API_KEY'] = get_api_key()
        subprocess.Popen(
            [LITELLM_PATH, '--config', config_path, '--port', '4000'],
            env=env, creationflags=subprocess.CREATE_NO_WINDOW
        )

    def _do_off(self):
        self._on = False
        self.btn.config(state=tk.DISABLED, text="Stopping...", bg="#999")
        self.status_label.config(fg="#e65100")

        def run():
            _stop_proxy()
            clear_all_vars()
            self.root.after(0, self._refresh_ui)

        threading.Thread(target=run, daemon=True).start()

    def _cleanup(self):
        _stop_proxy()
        clear_all_vars()

    def on_exit(self):
        self.root.withdraw()
        threading.Thread(target=self._shutdown_and_destroy, daemon=False).start()

    def _shutdown_and_destroy(self):
        self._cleanup()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
