"""Line-based PowerShell console tab (``+`` → Terminal)."""

from __future__ import annotations

import base64
import codecs
import os
from pathlib import Path

from PySide6.QtCore import QEvent, QProcess, Qt
from PySide6.QtGui import QFont, QKeyEvent, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from reader.theme import CARD, HOVER, INK, LINE, MUTED, PAPER

MARKER = "\x1e"
_EXITED = "[进程已退出]"
_STARTUP = (
    "$__u = [Text.UTF8Encoding]::new($false); "
    "[Console]::InputEncoding = $__u; [Console]::OutputEncoding = $__u; "
    "$OutputEncoding = $__u; Remove-Variable __u"
)
_REPORT_CWD = "[Console]::Out.WriteLine([char]30 + (Get-Location).ProviderPath)"


def _encoded_command(command: str) -> str:
    # PowerShell decodes piped stdin with the OEM code page, so ship the command
    # as ASCII Base64 of its UTF-8 bytes and evaluate it in the global scope.
    payload = base64.b64encode(command.encode("utf-8")).decode("ascii")
    return (
        "Invoke-Expression ([Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{payload}')))"
    )


def powershell_program() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = Path(root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return str(candidate) if candidate.is_file() else "powershell.exe"


class TerminalPage(QWidget):
    """Runs PowerShell over pipes; not a PTY, so full-screen TUIs are unsupported."""

    def __init__(self, cwd: Path | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("terminalPage")
        self._cwd = Path(cwd) if cwd is not None else Path.home()
        self._history: list[str] = []
        self._history_index = 0
        self._ready = False
        self._shutdown = False
        self._pending = ""
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._process: QProcess | None = None

        toolbar = QWidget(self)
        toolbar.setObjectName("terminalToolbar")
        toolbar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        toolbar.setFixedHeight(36)
        bar = QHBoxLayout(toolbar)
        bar.setContentsMargins(12, 4, 12, 4)
        bar.setSpacing(4)
        title = QLabel("PowerShell", toolbar)
        title.setObjectName("terminalTitle")
        bar.addWidget(title)
        bar.addStretch(1)
        self._clear_button = self._tool_button(toolbar, "terminalClear", "清屏")
        self._restart_button = self._tool_button(toolbar, "terminalRestart", "重启")
        bar.addWidget(self._clear_button)
        bar.addWidget(self._restart_button)

        mono = QFont("Cascadia Mono")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setFamilies(["Cascadia Mono", "Consolas", "Courier New"])
        mono.setPointSize(10)

        self._output = QPlainTextEdit(self)
        self._output.setObjectName("terminalOutput")
        self._output.setReadOnly(True)
        self._output.setFont(mono)
        self._output.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self._output.setMaximumBlockCount(5000)

        input_row = QWidget(self)
        input_row.setObjectName("terminalInputRow")
        input_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        row = QHBoxLayout(input_row)
        row.setContentsMargins(12, 6, 12, 8)
        row.setSpacing(6)
        self._prompt = QLabel(input_row)
        self._prompt.setObjectName("terminalPrompt")
        self._prompt.setFont(mono)
        self._input = QLineEdit(input_row)
        self._input.setObjectName("terminalInput")
        self._input.setFont(mono)
        self._input.setPlaceholderText("输入命令后回车")
        self._input.installEventFilter(self)
        row.addWidget(self._prompt)
        row.addWidget(self._input, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self._output, 1)
        layout.addWidget(input_row)

        self.setStyleSheet(
            f"""
            QWidget#terminalToolbar, QWidget#terminalInputRow {{
                background: {PAPER};
            }}
            QWidget#terminalToolbar {{ border-bottom: 1px solid {LINE}; }}
            QWidget#terminalInputRow {{ border-top: 1px solid {LINE}; }}
            QLabel#terminalTitle {{ color: {MUTED}; font-size: 12px; }}
            QLabel#terminalPrompt {{ color: {MUTED}; }}
            QToolButton#terminalClear, QToolButton#terminalRestart {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px 10px;
                color: {INK};
            }}
            QToolButton#terminalClear:hover, QToolButton#terminalRestart:hover {{
                background: {HOVER};
            }}
            QPlainTextEdit#terminalOutput {{
                background: {CARD};
                color: {INK};
                border: none;
                padding: 8px 12px;
            }}
            QLineEdit#terminalInput {{
                background: {CARD};
                color: {INK};
                border: 1px solid {LINE};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            """
        )

        self._clear_button.clicked.connect(self.clear)
        self._restart_button.clicked.connect(self.restart)
        self._input.returnPressed.connect(self._submit)
        self._update_prompt()
        self._start()

    @staticmethod
    def _tool_button(parent: QWidget, name: str, text: str) -> QToolButton:
        button = QToolButton(parent)
        button.setObjectName(name)
        button.setText(text)
        button.setAutoRaise(True)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return button

    def process(self) -> QProcess | None:
        return self._process

    def is_ready(self) -> bool:
        return self._ready

    def cwd(self) -> Path:
        return self._cwd

    def input_edit(self) -> QLineEdit:
        return self._input

    def focus_input(self) -> None:
        self._input.setFocus(Qt.FocusReason.OtherFocusReason)

    def clear(self) -> None:
        self._output.clear()

    def _start(self) -> None:
        self._ready = False
        self._pending = ""
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.setWorkingDirectory(str(self._cwd))
        process.readyReadStandardOutput.connect(self._read_output)
        process.finished.connect(lambda *_args, p=process: self._on_finished(p))
        self._process = process
        process.start(
            powershell_program(),
            ["-NoLogo", "-NoProfile", "-Command", "-"],
        )
        self._write(_STARTUP)
        self._write(_REPORT_CWD)

    def _stop(self, process: QProcess | None) -> None:
        if process is None:
            return
        try:
            process.readyReadStandardOutput.disconnect(self._read_output)
        except (RuntimeError, TypeError):
            pass
        try:
            process.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        if process.state() != QProcess.ProcessState.NotRunning:
            process.kill()
            process.waitForFinished(3000)
        process.deleteLater()

    def restart(self) -> None:
        if self._shutdown:
            return
        old = self._process
        self._process = None
        self._stop(old)
        self._append_lines(["[重新启动]"])
        self._start()

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        process = self._process
        self._stop(process)
        self._ready = False

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        self.shutdown()
        super().closeEvent(event)

    def _write(self, line: str) -> None:
        process = self._process
        if process is None or process.state() == QProcess.ProcessState.NotRunning:
            return
        process.write((line + "\n").encode("utf-8"))

    def _submit(self) -> None:
        command = self._input.text()
        self._input.clear()
        if command.strip():
            self._history.append(command)
        self._history_index = len(self._history)
        if command.strip().lower() in {"cls", "clear", "clear-host"}:
            self.clear()
            return
        self._append_lines([f"PS {self._cwd}> {command}"])
        if self._process is None or self._process.state() == QProcess.ProcessState.NotRunning:
            self._append_lines([_EXITED])
            return
        self._write(_encoded_command(command))
        self._write(_REPORT_CWD)

    def _read_output(self) -> None:
        process = self._process
        if process is None:
            return
        chunk = bytes(process.readAllStandardOutput().data())
        self._pending += self._decoder.decode(chunk)
        *lines, self._pending = self._pending.split("\n")
        shown: list[str] = []
        for raw in lines:
            line = raw.rstrip("\r")
            if line.startswith(MARKER):
                self._cwd = Path(line[len(MARKER):].strip() or str(self._cwd))
                self._ready = True
                self._update_prompt()
                continue
            shown.append(line.replace(MARKER, ""))
        if shown:
            self._append_lines(shown)

    def _on_finished(self, process: QProcess) -> None:
        if process is not self._process:
            return
        self._read_output()
        if self._pending:
            self._append_lines([self._pending.replace(MARKER, "")])
            self._pending = ""
        self._ready = False
        self._append_lines([_EXITED])

    def _append_lines(self, lines: list[str]) -> None:
        self._output.appendPlainText("\n".join(lines))
        self._output.moveCursor(QTextCursor.MoveOperation.End)

    def _update_prompt(self) -> None:
        self._prompt.setText(f"PS {self._cwd}>")

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if (
            watched is self._input
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key() in {Qt.Key.Key_Up, Qt.Key.Key_Down}
        ):
            if event.key() == Qt.Key.Key_Up:
                self._history_index = max(self._history_index - 1, 0)
            else:
                self._history_index = min(self._history_index + 1, len(self._history))
            if self._history_index < len(self._history):
                self._input.setText(self._history[self._history_index])
            else:
                self._input.clear()
            return True
        return super().eventFilter(watched, event)
