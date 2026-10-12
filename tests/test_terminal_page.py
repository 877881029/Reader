from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QPlainTextEdit, QToolButton

from reader.shell.terminal_page import MARKER, TerminalPage

TIMEOUT = 20000


@pytest.fixture
def terminal(qtbot, tmp_path: Path):
    page = TerminalPage(tmp_path)
    qtbot.addWidget(page)
    qtbot.waitUntil(page.is_ready, timeout=TIMEOUT)
    yield page
    page.shutdown()


def _output(page: TerminalPage) -> str:
    return page.findChild(QPlainTextEdit, "terminalOutput").toPlainText()


def _run(qtbot, page: TerminalPage, command: str) -> None:
    edit = page.findChild(QLineEdit, "terminalInput")
    edit.setText(command)
    qtbot.keyClick(edit, Qt.Key.Key_Return)


def test_widgets_and_start_directory(terminal: TerminalPage, tmp_path: Path):
    assert terminal.objectName() == "terminalPage"
    prompt = terminal.findChild(QLabel, "terminalPrompt")
    assert prompt is not None and str(tmp_path) in prompt.text()
    for name in ("terminalClear", "terminalRestart"):
        assert terminal.findChild(QToolButton, name) is not None
    assert terminal.findChild(QPlainTextEdit, "terminalOutput").isReadOnly()


def test_runs_command_and_shows_unicode_output_without_markers(qtbot, terminal):
    _run(qtbot, terminal, "Write-Output 'hello-reader 中文'")

    qtbot.waitUntil(
        lambda: "hello-reader 中文" in _output(terminal).splitlines(), timeout=TIMEOUT
    )
    assert MARKER not in _output(terminal)
    assert "> Write-Output 'hello-reader 中文'" in _output(terminal)


def test_prompt_follows_set_location(qtbot, terminal, tmp_path: Path):
    child = tmp_path / "sub dir"
    child.mkdir()
    _run(qtbot, terminal, f"Set-Location '{child}'")

    prompt = terminal.findChild(QLabel, "terminalPrompt")
    qtbot.waitUntil(lambda: str(child) in prompt.text(), timeout=TIMEOUT)
    assert terminal.cwd() == child


def test_history_and_cls(qtbot, terminal):
    edit = terminal.findChild(QLineEdit, "terminalInput")
    _run(qtbot, terminal, "Write-Output one")
    _run(qtbot, terminal, "Write-Output two")
    qtbot.waitUntil(lambda: "two" in _output(terminal).splitlines(), timeout=TIMEOUT)

    qtbot.keyClick(edit, Qt.Key.Key_Up)
    assert edit.text() == "Write-Output two"
    qtbot.keyClick(edit, Qt.Key.Key_Up)
    assert edit.text() == "Write-Output one"
    qtbot.keyClick(edit, Qt.Key.Key_Down)
    assert edit.text() == "Write-Output two"
    qtbot.keyClick(edit, Qt.Key.Key_Down)
    assert edit.text() == ""

    _run(qtbot, terminal, "cls")
    assert _output(terminal) == ""


def test_restart_and_shutdown_stop_process(qtbot, terminal):
    first = terminal.process()
    terminal.findChild(QToolButton, "terminalRestart").click()
    qtbot.waitUntil(terminal.is_ready, timeout=TIMEOUT)
    assert terminal.process() is not first
    _run(qtbot, terminal, "Write-Output after-restart")
    qtbot.waitUntil(lambda: "after-restart" in _output(terminal), timeout=TIMEOUT)

    process = terminal.process()
    terminal.shutdown()
    assert process.state() == QProcess.ProcessState.NotRunning


def test_exit_shows_process_exited(qtbot, terminal):
    _run(qtbot, terminal, "exit")
    qtbot.waitUntil(lambda: "[进程已退出]" in _output(terminal), timeout=TIMEOUT)
