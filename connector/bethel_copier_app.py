"""Customer-facing Bethel Copier setup and background launcher for Windows."""
import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import MetaTrader5 as mt5
import numpy as np
import requests


API = "https://bethel-api.onrender.com"
APP_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / "BethelCopier"
CONFIG_FILE = APP_DIR / "config.json"
TOKEN_FILE = APP_DIR / "receiver-token.dpapi"
LOG_FILE = APP_DIR / "subscriber-copier.log"
STATE_FILE = APP_DIR / "subscriber-state.json"
TASK_NAME = "Bethel Subscriber Copier"


def packaged_self_test():
    if os.name != "nt":
        raise RuntimeError("Bethel Copier requires Windows")
    if ctypes.sizeof(ctypes.c_void_p) != 8:
        raise RuntimeError("Bethel Copier requires 64-bit Windows")
    probe = np.array([1.0, 2.0], dtype=float)
    if float(probe.sum()) != 3.0 or not hasattr(mt5, "initialize"):
        raise RuntimeError("Packaged NumPy/MetaTrader5 runtime validation failed")


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer


def protect(value: str):
    source, source_buffer = _blob(value.encode())
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(ctypes.byref(source), "Bethel Copier", None, None, None, 0, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(output.pbData, output.cbData)
        return base64.b64encode(encrypted).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def unprotect(value: str):
    source, source_buffer = _blob(base64.b64decode(value))
    output = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode()
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def terminal_candidates():
    roots = [Path(os.getenv("PROGRAMFILES", "C:/Program Files")), Path(os.getenv("PROGRAMFILES(X86)", "C:/Program Files (x86)")), Path(os.getenv("APPDATA", Path.home())) / "MetaQuotes" / "Terminal"]
    found = []
    for root in roots:
        if not root.exists():
            continue
        try:
            for path in root.glob("**/terminal64.exe"):
                text = str(path)
                if text not in found:
                    found.append(text)
        except OSError:
            continue
    return found


def terminal_details(path):
    mt5.shutdown()
    if not mt5.initialize(path=path):
        raise RuntimeError(f"Could not connect to this MT5 terminal: {mt5.last_error()}")
    account = mt5.account_info()
    if account is None:
        raise RuntimeError("Log in to the subscriber account inside MT5 first")
    if str(account.login) == "49617874":
        raise RuntimeError("The master account cannot be connected as a subscriber")
    symbols = mt5.symbols_get() or []
    info = next((item for item in symbols if item.trade_contract_size > 0 and item.volume_step > 0), None)
    if info is None:
        raise RuntimeError("No tradable symbol metadata is available")
    currency = str(account.currency).upper()
    cent = currency in {"USC", "USCENT", "USCENTS", "CENT"}
    return account, {
        "account_number": str(account.login),
        "environment": "DEMO" if "demo" in str(account.server).casefold() else "LIVE",
        "server": str(account.server), "leverage": int(account.leverage or 0),
        "currency_unit": "USC" if cent else "USD", "is_cent_account": cent,
        "contract_size": info.trade_contract_size, "min_lot": info.volume_min,
        "max_lot": info.volume_max, "lot_step": info.volume_step,
    }


def install_background(config, token):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(protect(token), encoding="utf-8")
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
    executable = Path(sys.executable).resolve()
    command = f'"{executable}" --service'
    result = subprocess.run(["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", TASK_NAME, "/TR", command, "/RL", "LIMITED"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Windows could not install automatic startup")
    subprocess.run(["schtasks", "/Run", "/TN", TASK_NAME], capture_output=True)


def service_mode():
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    token = unprotect(TOKEN_FILE.read_text(encoding="utf-8"))
    os.environ.update({
        "BETHEL_RECEIVER_TOKEN": token, "BETHEL_API_URL": API,
        "BETHEL_SUBSCRIBER_ACCOUNT": config["account"],
        "BETHEL_SUBSCRIBER_MODE": config["mode"],
        "BETHEL_SUBSCRIBER_TERMINAL_PATH": config["terminal_path"],
        "BETHEL_ALLOW_LIVE": "true" if config["mode"] == "LIVE" else "false",
        "BETHEL_COPIER_LOG": str(LOG_FILE), "BETHEL_COPIER_STATE": str(STATE_FILE),
    })
    from connector.mt5_subscriber_copier import run
    run()


class SetupApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bethel Copier")
        self.geometry("640x430")
        self.resizable(False, False)
        self.configure(bg="#071426")
        self.terminal = tk.StringVar()
        self.code = tk.StringVar()
        self.status = tk.StringVar(value="Detecting MetaTrader 5 installations…")
        self._build()
        threading.Thread(target=self._detect, daemon=True).start()

    def _build(self):
        style = ttk.Style(self); style.theme_use("clam")
        style.configure("TFrame", background="#071426"); style.configure("TLabel", background="#071426", foreground="#e8f1ff", font=("Segoe UI", 11)); style.configure("Title.TLabel", font=("Segoe UI Semibold", 23), foreground="#55d6ff")
        frame = ttk.Frame(self, padding=36); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="BETHEL COPIER", style="Title.TLabel").pack(anchor="w")
        ttk.Label(frame, text="Secure automatic master-to-subscriber copying", foreground="#9fb3c8").pack(anchor="w", pady=(4, 28))
        ttk.Label(frame, text="MetaTrader 5 terminal").pack(anchor="w")
        self.terminals = ttk.Combobox(frame, textvariable=self.terminal, width=76, state="readonly"); self.terminals.pack(fill="x", pady=(6, 18))
        ttk.Label(frame, text="One-time activation code").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.code, width=76).pack(fill="x", pady=(6, 22))
        self.connect_button = ttk.Button(frame, text="Connect Bethel Copier", command=self._connect, state="disabled"); self.connect_button.pack(fill="x", ipady=8)
        ttk.Label(frame, textvariable=self.status, foreground="#77e1a6", wraplength=560).pack(anchor="w", pady=(20, 0))
        ttk.Label(frame, text="Bethel never requests or stores your MT5 trading password.", foreground="#9fb3c8").pack(anchor="w", pady=(22, 0))

    def _detect(self):
        found = terminal_candidates()
        self.after(0, lambda: self._detected(found))

    def _detected(self, found):
        self.terminals["values"] = found
        if found:
            self.terminal.set(found[0]); self.connect_button["state"] = "normal"; self.status.set("MT5 detected. Enter the activation code from your Bethel dashboard.")
        else:
            self.status.set("No MT5 terminal was detected. Install and log in to MetaTrader 5, then reopen Bethel Copier.")

    def _connect(self):
        if len(self.code.get().strip()) < 20:
            messagebox.showerror("Activation required", "Enter the complete one-time activation code."); return
        self.connect_button["state"] = "disabled"; self.status.set("Verifying MT5 and activating securely…")
        threading.Thread(target=self._activate, daemon=True).start()

    def _activate(self):
        try:
            account, metadata = terminal_details(self.terminal.get())
            response = requests.post(API + "/copyhub/v1/receiver/activate", json={"activation_code": self.code.get().strip(), **metadata}, timeout=30)
            if not response.ok:
                detail = response.json().get("detail", response.text) if "application/json" in response.headers.get("content-type", "") else response.text
                raise RuntimeError(detail)
            data = response.json()
            install_background({"account": str(account.login), "mode": metadata["environment"], "terminal_path": self.terminal.get()}, data["receiver_token"])
            self.after(0, lambda: self._success(data))
        except Exception as error:
            self.after(0, lambda: self._failure(str(error)))

    def _success(self, data):
        self.status.set("Connected successfully. Bethel Copier will start automatically with Windows.")
        messagebox.showinfo("Bethel Copier connected", "Connection complete. Copying remains subject to your subscription and Bethel safety controls.")

    def _failure(self, message):
        self.connect_button["state"] = "normal"; self.status.set("Connection failed. Check the account and activation code.")
        messagebox.showerror("Unable to connect", message)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        packaged_self_test()
    elif "--service" in sys.argv:
        service_mode()
    else:
        SetupApp().mainloop()
