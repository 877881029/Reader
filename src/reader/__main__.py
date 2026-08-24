from __future__ import annotations

import os
import sys

from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

from reader.app import ReaderApp, set_app_user_model_id
from reader.ipc import SingleInstance, server_name
from reader.shell.associate import create_desktop_shortcut, register_open_with


def _server_running() -> bool:
    sock = QLocalSocket()
    sock.connectToServer(server_name())
    connected = sock.waitForConnected(200)
    sock.disconnectFromServer()
    return connected


def _association_target() -> tuple[str, tuple[str, ...]]:
    if getattr(sys, "frozen", False):
        return sys.executable, ()
    return sys.executable, ("-m", "reader")


def _shell_integration_disabled() -> bool:
    value = os.environ.get("READER_SKIP_SHELL_INTEGRATION", "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    files = [arg for arg in argv[1:] if not arg.startswith("-")]
    set_app_user_model_id()

    if _server_running():
        SingleInstance.send_paths(files)
        return 0

    qapp = QApplication.instance() or QApplication(argv)
    app = ReaderApp(qapp)
    if not app.is_primary_instance():
        SingleInstance.send_paths(files)
        return 0

    win = app.new_window()
    if files:
        win.open_paths(files)

    if not _shell_integration_disabled():
        try:
            exe, args = _association_target()
            register_open_with(exe, args=args)
            create_desktop_shortcut(exe, args=args, icon=exe)
        except Exception:
            pass

    return qapp.exec()


if __name__ == "__main__":
    raise SystemExit(main())
