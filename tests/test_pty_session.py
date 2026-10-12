from __future__ import annotations

import re
from pathlib import Path

import pytest

from reader.terminal.pty_session import DA1_RESPONSE, SHELL_PROFILES, PtySession

TIMEOUT = 20000
_ANSI = re.compile(r"\x1b(\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(\x07|\x1b\\))")


def _plain(chunks: list[str]) -> str:
    return _ANSI.sub("", "".join(chunks))


def _start(qtbot, profile: str, cwd: Path, cols: int = 100, rows: int = 30):
    session = PtySession(profile, cwd)
    chunks: list[str] = []
    exits: list[int] = []
    session.output.connect(chunks.append)
    session.exited.connect(exits.append)
    session.start(cols, rows)
    # xterm.js answers ConPTY's device-attributes query; emulate it here.
    session.write(DA1_RESPONSE)
    return session, chunks, exits


def test_profiles_use_absolute_system_shells():
    assert set(SHELL_PROFILES) == {"powershell", "cmd"}
    assert SHELL_PROFILES["powershell"].title == "PowerShell"
    assert SHELL_PROFILES["cmd"].title == "Command Prompt"
    for profile in SHELL_PROFILES.values():
        program = Path(profile.argv[0])
        assert program.is_absolute() and program.is_file()
    assert SHELL_PROFILES["powershell"].argv[1:] == ["-NoLogo"]


def test_cmd_runs_command_with_unicode_in_start_dir(qtbot, tmp_path: Path):
    session, chunks, _exits = _start(qtbot, "cmd", tmp_path)
    try:
        session.write("echo READER_PTY_OK 中文\r")
        qtbot.waitUntil(lambda: "".join(chunks).count("READER_PTY_OK 中文") >= 2, timeout=TIMEOUT)
        session.write("cd\r")
        qtbot.waitUntil(lambda: str(tmp_path) in "".join(chunks), timeout=TIMEOUT)
    finally:
        session.shutdown()


def test_resize_reaches_console(qtbot, tmp_path: Path):
    session, chunks, _exits = _start(qtbot, "cmd", tmp_path)
    try:
        session.resize(123, 41)
        session.write("mode con\r")
        qtbot.waitUntil(lambda: "123" in "".join(chunks).split("mode con")[-1], timeout=TIMEOUT)
        assert "41" in "".join(chunks).split("mode con")[-1]
    finally:
        session.shutdown()


def test_powershell_evaluates(qtbot, tmp_path: Path):
    session, chunks, _exits = _start(qtbot, "powershell", tmp_path)
    try:
        session.write("Write-Output ('REA' + 'DER')\r")
        qtbot.waitUntil(lambda: "\nREADER\r" in _plain(chunks), timeout=TIMEOUT)
    finally:
        session.shutdown()


def test_exit_emits_exited_and_shutdown_is_quiet(qtbot, tmp_path: Path):
    session, _chunks, exits = _start(qtbot, "cmd", tmp_path)
    session.write("exit 3\r")
    qtbot.waitUntil(lambda: bool(exits), timeout=TIMEOUT)
    assert session.is_running() is False
    session.shutdown()

    other, _chunks2, other_exits = _start(qtbot, "cmd", tmp_path)
    assert other.is_running() is True
    other.shutdown()
    assert other.is_running() is False
    qtbot.wait(300)
    assert other_exits == []
    other.write("echo after\r")


def test_unknown_profile_rejected(tmp_path: Path):
    with pytest.raises(KeyError):
        PtySession("bash", tmp_path)
