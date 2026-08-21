from __future__ import annotations

import ctypes
import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from reader.ipc import SingleInstance
from reader.shell.window import MainWindow, PreviewExecutor

APP_USER_MODEL_ID = "Reader.Desktop"


def set_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> None:
    if platform.system() != "Windows":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return


class ReaderApp:
    def __init__(self, qapp: QApplication, *, ipc: SingleInstance | None = None) -> None:
        self._qapp = qapp
        self._windows: list[MainWindow] = []
        self._executor = PreviewExecutor(parent=qapp)
        self._ipc = ipc if ipc is not None else SingleInstance()
        self._is_primary = self._ipc.become_server(self._on_ipc_paths)
        self._ipc_closed = False

    def _on_ipc_paths(self, paths: list[str]) -> None:
        window = self._windows[-1] if self._windows else self.new_window()
        window.open_paths(paths)
        window.setWindowState(
            window.windowState() & ~Qt.WindowState.WindowMinimized
            | Qt.WindowState.WindowActive
        )
        window.raise_()
        window.activateWindow()

    def new_window(self) -> MainWindow:
        window = MainWindow(
            on_new_window=self.new_window,
            executor=self._executor,
        )
        window_id = id(window)
        window.destroyed.connect(
            lambda *_args, target_id=window_id: self._drop(target_id)
        )
        self._windows.append(window)
        window.show()
        return window

    def _drop(self, window_id: int) -> None:
        self._windows = [item for item in self._windows if id(item) != window_id]
        if not self._windows:
            self._close_ipc()

    def _close_ipc(self) -> None:
        if self._ipc_closed:
            return
        self._ipc.close()
        self._ipc_closed = True

    def is_primary_instance(self) -> bool:
        return self._is_primary

    def window_count(self) -> int:
        return len(self._windows)

    def close_all(self) -> None:
        for window in list(self._windows):
            window.close()
        self._close_ipc()
