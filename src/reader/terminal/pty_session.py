"""Shell process attached to a Windows pseudo console (ConPTY via pywinpty)."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal, Slot

# Primary device attributes reply ("VT100 with advanced video"); xterm.js sends
# the same when ConPTY asks, tests and selftests send it themselves.
DA1_RESPONSE = "\x1b[?1;2c"


@dataclass(frozen=True)
class ShellProfile:
    title: str
    argv: list[str]


def _system32() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"


SHELL_PROFILES: dict[str, ShellProfile] = {
    "powershell": ShellProfile(
        "PowerShell",
        [str(_system32() / "WindowsPowerShell" / "v1.0" / "powershell.exe"), "-NoLogo"],
    ),
    "cmd": ShellProfile("Command Prompt", [str(_system32() / "cmd.exe")]),
}


class PtySession(QObject):
    """Owns one shell process; output is delivered on the Qt main thread."""

    output = Signal(str)
    exited = Signal(int)
    _chunk = Signal(str)
    _finished = Signal(int)

    def __init__(self, profile: str, cwd: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.profile_key = profile
        self.profile = SHELL_PROFILES[profile]
        self.cwd = Path(cwd)
        self._pty = None
        self._thread: threading.Thread | None = None
        self._closing = False
        self._chunk.connect(self._deliver, Qt.ConnectionType.QueuedConnection)
        self._finished.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)

    def start(self, cols: int, rows: int) -> None:
        from winpty import PtyProcess

        self._closing = False
        self._pty = PtyProcess.spawn(
            self.profile.argv,
            cwd=str(self.cwd),
            dimensions=(max(int(rows), 1), max(int(cols), 1)),
        )
        pty = self._pty
        self._thread = threading.Thread(target=self._read_loop, args=(pty,), daemon=True)
        self._thread.start()

    def is_running(self) -> bool:
        return self._pty is not None and bool(self._pty.isalive())

    def write(self, data: str) -> None:
        if self.is_running() and data:
            try:
                self._pty.write(data)
            except Exception:
                pass

    def resize(self, cols: int, rows: int) -> None:
        if self.is_running():
            try:
                self._pty.setwinsize(max(int(rows), 1), max(int(cols), 1))
            except Exception:
                pass

    def shutdown(self) -> None:
        self._closing = True
        pty, self._pty = self._pty, None
        if pty is not None:
            try:
                if pty.isalive():
                    pty.terminate(force=True)
            except Exception:
                pass
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=2.0)

    def _read_loop(self, pty) -> None:
        while True:
            try:
                data = pty.read(65536)
            except EOFError:
                break
            except Exception:
                break
            if data:
                self._chunk.emit(data)
            elif not pty.isalive():
                break
        code = pty.exitstatus if pty.exitstatus is not None else -1
        self._finished.emit(int(code))

    @Slot(str)
    def _deliver(self, data: str) -> None:
        if not self._closing:
            self.output.emit(data)

    @Slot(int)
    def _on_finished(self, code: int) -> None:
        if not self._closing:
            self._pty = None
            self.exited.emit(code)