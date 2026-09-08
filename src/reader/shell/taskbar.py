from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

DWMWA_FORCE_ICONIC_REPRESENTATION = 7
APP_USER_MODEL_ID = "Reader.Desktop"


def force_iconic_representation(hwnd: int) -> bool:
    if os.name != "nt" or hwnd == 0:
        return False
    value = ctypes.c_int(1)
    try:
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_FORCE_ICONIC_REPRESENTATION,
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        return False
    return int(result) == 0


def apply_hwnd_app_user_model(hwnd: int, icon_path: Path) -> bool:
    if os.name != "nt" or hwnd == 0:
        return False
    try:
        from win32com.propsys import propsys, pscon
    except ImportError:
        return False
    resolved_icon = Path(icon_path).resolve()
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
        icon_res = f"{sys.executable},0"
    else:
        command = f'"{sys.executable}" -m reader'
        icon_res = f"{resolved_icon},0"
    try:
        store = propsys.SHGetPropertyStoreForWindow(hwnd)
        store.SetValue(
            pscon.PKEY_AppUserModel_ID,
            propsys.PROPVARIANTType(APP_USER_MODEL_ID),
        )
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchCommand,
            propsys.PROPVARIANTType(command),
        )
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchIconResource,
            propsys.PROPVARIANTType(icon_res),
        )
        store.SetValue(
            pscon.PKEY_AppUserModel_RelaunchDisplayNameResource,
            propsys.PROPVARIANTType("Reader"),
        )
        store.Commit()
        return True
    except Exception:
        return False
