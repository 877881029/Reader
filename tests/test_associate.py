from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from reader.shell.associate import EXTENSIONS, PROGID, create_desktop_shortcut, register_open_with


class FakeKey:
    def __init__(self) -> None:
        self.values: dict[object, str] = {}
        self.closed = False

    def Close(self) -> None:
        self.closed = True


class FakeWinreg:
    HKEY_CURRENT_USER = object()
    REG_SZ = 1

    def __init__(self, *, fail_on_name: str | None = None) -> None:
        self.fail_on_name = fail_on_name
        self.created: list[str] = []
        self.keys: dict[str, FakeKey] = {}

    def CreateKey(self, _root, path: str) -> FakeKey:
        key = FakeKey()
        self.created.append(path)
        self.keys[path] = key
        return key

    def SetValueEx(self, key: FakeKey, name, _reserved: int, _typ: int, value: str) -> None:
        if self.fail_on_name is not None and name == self.fail_on_name:
            raise OSError("injected registry failure")
        key.values[name] = value


def test_register_open_with_hkcu_classes_only_and_close_keys() -> None:
    wr = FakeWinreg()
    register_open_with(r"C:\Reader\reader.exe", winreg_module=wr)

    command_path = r"Software\Classes\Reader.Document\shell\open\command"
    assert PROGID == "Reader.Document"
    assert EXTENSIONS == (".docx", ".pptx", ".xlsx", ".md")
    assert all(path.startswith("Software\\Classes\\") for path in wr.created)
    assert all("UserChoice" not in path for path in wr.created)
    assert command_path in wr.created
    for ext in EXTENSIONS:
        assert rf"Software\Classes\{ext}\OpenWithProgids" in wr.created
    assert wr.keys[command_path].values[None] == subprocess.list2cmdline([r"C:\Reader\reader.exe"]) + ' "%1"'
    assert all(key.closed for key in wr.keys.values())


def test_register_open_with_sets_default_icon_to_exe() -> None:
    wr = FakeWinreg()
    register_open_with(r"C:\Reader\Reader.exe", winreg_module=wr)

    assert wr.keys[r"Software\Classes\Reader.Document\DefaultIcon"].values[None] == r"C:\Reader\Reader.exe,0"
    assert wr.keys[r"Software\Classes\Reader.Document\shell\open\command"].values[None] == (
        subprocess.list2cmdline([r"C:\Reader\Reader.exe"]) + ' "%1"'
    )


def test_register_open_with_formats_development_python_module_command() -> None:
    wr = FakeWinreg()
    register_open_with(r"C:\Python312\python.exe", args=("-m", "reader"), winreg_module=wr)

    assert wr.keys[r"Software\Classes\Reader.Document\DefaultIcon"].values[None] == r"C:\Python312\python.exe,0"
    assert wr.keys[r"Software\Classes\Reader.Document\shell\open\command"].values[None] == (
        subprocess.list2cmdline([r"C:\Python312\python.exe", "-m", "reader"]) + ' "%1"'
    )


def test_register_open_with_handles_program_files_and_quoted_percent1_suffix() -> None:
    wr = FakeWinreg()
    exe = r"C:\Program Files\Reader\Reader.exe"
    args = ("-m", "reader", "--name=space value", "tab\tvalue", 'say "hi"', r"trail\\")

    register_open_with(exe, args=args, winreg_module=wr)

    command = wr.keys[r"Software\Classes\Reader.Document\shell\open\command"].values[None]
    assert command == subprocess.list2cmdline([exe, *args]) + ' "%1"'
    assert command.endswith(' "%1"')
    assert wr.keys[r"Software\Classes\Reader.Document\DefaultIcon"].values[None] == f"{exe},0"


def test_register_open_with_propagates_errors() -> None:
    wr = FakeWinreg(fail_on_name=PROGID)
    with pytest.raises(OSError):
        register_open_with(r"C:\Reader\reader.exe", winreg_module=wr)


class FakeShortcut:
    def __init__(self) -> None:
        self.Targetpath = ""
        self.Arguments = ""
        self.WorkingDirectory = ""
        self.Description = ""
        self.IconLocation = ""
        self.saved = False

    def Save(self) -> None:
        self.saved = True


class FakeWScriptShell:
    def __init__(self) -> None:
        self.shortcut_paths: list[str] = []
        self.shortcuts: list[FakeShortcut] = []

    def CreateShortCut(self, path: str) -> FakeShortcut:
        shortcut = FakeShortcut()
        self.shortcut_paths.append(path)
        self.shortcuts.append(shortcut)
        return shortcut


class FakeComModule:
    def __init__(self) -> None:
        self.shell = FakeWScriptShell()

    def Dispatch(self, prog_id: str) -> FakeWScriptShell:
        assert prog_id == "WScript.Shell"
        return self.shell


def test_create_desktop_shortcut_uses_known_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("reader.shell.associate._desktop_known_location", lambda: tmp_path / "KnownDesktop")
    com = FakeComModule()

    path = create_desktop_shortcut(r"C:\Reader\reader.exe", winshell_or_com=com)

    assert path == tmp_path / "KnownDesktop" / "Reader.lnk"
    shortcut = com.shell.shortcuts[0]
    assert shortcut.Targetpath == r"C:\Reader\reader.exe"
    assert shortcut.Arguments == ""
    assert shortcut.WorkingDirectory == r"C:\Reader"
    assert shortcut.IconLocation == r"C:\Reader\reader.exe,0"
    assert shortcut.Description == "Reader"
    assert shortcut.saved is True


def test_create_desktop_shortcut_falls_back_userprofile(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("reader.shell.associate._desktop_known_location", lambda: None)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    com = FakeComModule()

    path = create_desktop_shortcut(
        r"C:\Reader\reader.exe",
        name="Reader App",
        winshell_or_com=com,
    )

    assert path == tmp_path / "Desktop" / "Reader App.lnk"


def test_create_desktop_shortcut_sets_icon_location(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("reader.shell.associate._desktop_known_location", lambda: tmp_path / "KnownDesktop")
    com = FakeComModule()

    create_desktop_shortcut(r"C:\Reader\Reader.exe", winshell_or_com=com)

    shortcut = com.shell.shortcuts[0]
    assert shortcut.Targetpath == r"C:\Reader\Reader.exe"
    assert shortcut.WorkingDirectory == r"C:\Reader"
    assert shortcut.IconLocation == r"C:\Reader\Reader.exe,0"


def test_create_desktop_shortcut_uses_list2cmdline_for_arguments(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("reader.shell.associate._desktop_known_location", lambda: tmp_path / "KnownDesktop")
    com = FakeComModule()
    exe = r"C:\Program Files\Reader\Reader.exe"
    args = ("-m", "reader", "--name=space value", "tab\tvalue", 'say "hi"', r"trail\\")

    create_desktop_shortcut(exe, args=args, winshell_or_com=com)

    shortcut = com.shell.shortcuts[0]
    assert shortcut.Targetpath == exe
    assert shortcut.Arguments == subprocess.list2cmdline(list(args))
    assert shortcut.IconLocation == f"{exe},0"
