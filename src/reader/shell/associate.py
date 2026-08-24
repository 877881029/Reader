from __future__ import annotations

import ctypes
import os
import subprocess
from pathlib import Path
from uuid import UUID

PROGID = "Reader.Document"
EXTENSIONS = (".docx", ".pptx", ".xlsx", ".md")


def _set_reg_sz(wr, path: str, name: str | None, value: str) -> None:
    key = wr.CreateKey(wr.HKEY_CURRENT_USER, path)
    try:
        wr.SetValueEx(key, name, 0, wr.REG_SZ, value)
    finally:
        close = getattr(key, "Close", None)
        if callable(close):
            close()
        else:
            exit_fn = getattr(key, "__exit__", None)
            if callable(exit_fn):
                exit_fn(None, None, None)


def register_open_with(exe: str, winreg_module=None, *, args: tuple[str, ...] = ()) -> None:
    import winreg as default_winreg

    wr = winreg_module or default_winreg
    command = subprocess.list2cmdline([exe, *args]) + ' "%1"'
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\DefaultIcon", None, f"{exe},0")
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\shell\open\command", None, command)
    for ext in EXTENSIONS:
        _set_reg_sz(wr, rf"Software\Classes\{ext}\OpenWithProgids", PROGID, "")


def _desktop_known_location() -> Path | None:
    if os.name != "nt":
        return None

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_uint32),
            ("Data2", ctypes.c_uint16),
            ("Data3", ctypes.c_uint16),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    folder_id = UUID("B4BFCC3A-DB2C-424C-B029-7FE99A87C641")
    guid = GUID(
        folder_id.time_low,
        folder_id.time_mid,
        folder_id.time_hi_version,
        (ctypes.c_ubyte * 8)(*folder_id.bytes[8:]),
    )
    path_ptr = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(guid),
        0,
        None,
        ctypes.byref(path_ptr),
    )
    if result != 0 or not path_ptr.value:
        return None
    try:
        return Path(path_ptr.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)


def _desktop_path() -> Path:
    known = _desktop_known_location()
    if known is not None:
        return known
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        return Path(user_profile) / "Desktop"
    return Path.home() / "Desktop"


def create_desktop_shortcut(
    exe: str,
    name: str = "Reader",
    winshell_or_com=None,
    *,
    args: tuple[str, ...] = (),
    icon: str | None = None,
) -> Path:
    desktop = _desktop_path()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop / f"{name}.lnk"

    if winshell_or_com is None:
        import win32com.client as winshell_or_com

    shell = winshell_or_com.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = exe
    shortcut.Arguments = subprocess.list2cmdline(list(args)) if args else ""
    shortcut.WorkingDirectory = str(Path(exe).parent)
    shortcut.Description = name
    icon_location = icon or exe
    if "," not in icon_location:
        icon_location = f"{icon_location},0"
    shortcut.IconLocation = icon_location
    save = getattr(shortcut, "Save", None) or getattr(shortcut, "save")
    save()
    return shortcut_path
