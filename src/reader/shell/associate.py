from __future__ import annotations

import ctypes
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from uuid import UUID

PROGID = "Reader.Document"
EXTENSIONS = (
    ".docx",
    ".pptx",
    ".xlsx",
    ".md",
    ".pdf",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".svg",
)
_ICON_INDEX_RE = re.compile(r'^(?:"(?P<quoted>.*)"|(?P<plain>.*)),(?P<index>-?\d+)$')


def _icon_location(value: str) -> str:
    match = _ICON_INDEX_RE.fullmatch(value)
    if match is None:
        path = value
        index = "0"
    else:
        path = match.group("quoted") or match.group("plain")
        index = match.group("index")
    formatted_path = f'"{path}"' if any(char.isspace() for char in path) else path
    return f"{formatted_path},{index}"


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


def _try_delete_key(wr, path: str) -> None:
    delete = getattr(wr, "DeleteKey", None)
    if not callable(delete):
        return
    try:
        delete(wr.HKEY_CURRENT_USER, path)
    except FileNotFoundError:
        return
    except OSError:
        return


def _clear_user_choice(wr, ext: str) -> None:
    base = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}"
    _try_delete_key(wr, rf"{base}\UserChoice")
    _try_delete_key(wr, rf"{base}\UserChoiceLatest\ProgId")
    _try_delete_key(wr, rf"{base}\UserChoiceLatest")


def _notify_assoc_changed() -> None:
    try:
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        return


def register_open_with(
    exe: str,
    winreg_module=None,
    *,
    args: tuple[str, ...] = (),
    protected_claimer=None,
) -> None:
    import winreg as default_winreg

    wr = winreg_module or default_winreg
    command = subprocess.list2cmdline([exe, *args]) + ' "%1"'
    _set_reg_sz(wr, r"Software\Classes\Reader.Document", None, "Reader 文档")
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\DefaultIcon", None, _icon_location(exe))
    _set_reg_sz(wr, r"Software\Classes\Reader.Document\shell\open\command", None, command)
    _set_reg_sz(wr, r"Software\Reader\Capabilities", "ApplicationName", "Reader")
    _set_reg_sz(wr, r"Software\Reader\Capabilities", "ApplicationDescription", "Reader")
    _set_reg_sz(wr, r"Software\RegisteredApplications", "Reader", r"Software\Reader\Capabilities")
    for ext in EXTENSIONS:
        _set_reg_sz(wr, rf"Software\Classes\{ext}", None, PROGID)
        _set_reg_sz(wr, rf"Software\Classes\{ext}\OpenWithProgids", PROGID, "")
        _set_reg_sz(
            wr,
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithProgids",
            PROGID,
            "",
        )
        _set_reg_sz(
            wr,
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithList",
            "a",
            "Reader.exe",
        )
        _set_reg_sz(
            wr,
            rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{ext}\OpenWithList",
            "MRUList",
            "a",
        )
        _set_reg_sz(wr, r"Software\Reader\Capabilities\FileAssociations", ext, PROGID)
        _clear_user_choice(wr, ext)
    if winreg_module is None:
        _notify_assoc_changed()
        if protected_claimer is None:
            from reader.shell.settings_claim import claim_protected_defaults

            protected_claimer = claim_protected_defaults
    if protected_claimer is not None:
        protected_claimer()


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


def _set_shortcut_app_id(shortcut_path: Path, app_id: str) -> None:
    if os.name != "nt" or not shortcut_path.exists():
        return
    try:
        import pythoncom
        from win32com.propsys import propsys, pscon
    except ImportError:
        return
    try:
        pythoncom.CoInitialize()
        store = propsys.SHGetPropertyStoreFromParsingName(str(shortcut_path))
        store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(app_id))
        store.Commit()
    except Exception:
        return


def create_desktop_shortcut(
    exe: str,
    name: str = "Reader",
    winshell_or_com=None,
    *,
    args: tuple[str, ...] = (),
    icon: str | None = None,
    overwrite: bool = False,
    app_id_setter: Callable[[Path, str], None] | None = None,
) -> Path:
    desktop = _desktop_path()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut_path = desktop / f"{name}.lnk"
    if shortcut_path.exists() and not overwrite:
        return shortcut_path

    if winshell_or_com is None:
        import win32com.client as winshell_or_com

    shell = winshell_or_com.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = exe
    shortcut.Arguments = subprocess.list2cmdline(list(args)) if args else ""
    shortcut.WorkingDirectory = str(Path(exe).parent)
    shortcut.Description = name
    shortcut.IconLocation = _icon_location(icon or exe)
    save = getattr(shortcut, "Save", None) or getattr(shortcut, "save")
    save()
    setter = app_id_setter if app_id_setter is not None else _set_shortcut_app_id
    try:
        from reader.app import APP_USER_MODEL_ID

        setter(shortcut_path, APP_USER_MODEL_ID)
    except Exception:
        pass
    return shortcut_path
