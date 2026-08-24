from __future__ import annotations

import ctypes
import platform
import sys
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from reader.ipc import SingleInstance
from reader.resources import resource_path
from reader.shell.window import MainWindow, PreviewExecutor
from reader.smoke import append_smoke_batch

APP_USER_MODEL_ID = "Reader.Desktop"


def set_app_user_model_id(
    app_id: str = APP_USER_MODEL_ID,
    *,
    setter: Callable[[str], None] | None = None,
) -> None:
    if platform.system() != "Windows":
        return
    try:
        if setter is not None:
            setter(app_id)
        else:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except (AttributeError, OSError):
        return


def _reader_icon_path() -> Path:
    return resource_path("assets", "icons", "reader.ico")


def _load_icon_if_exists(icon_path: Path, icon_applier: Callable[[QIcon], None]) -> bool:
    if not icon_path.exists():
        return False
    icon_applier(QIcon(str(icon_path)))
    return True


class ReaderApp:
    def __init__(
        self,
        qapp: QApplication,
        *,
        ipc: SingleInstance | None = None,
        icon_path_provider: Callable[[], Path] | None = None,
        icon_applier: Callable[[QIcon], None] | None = None,
    ) -> None:
        self._qapp = qapp
        icon_path = (
            icon_path_provider() if icon_path_provider is not None else _reader_icon_path()
        )
        _load_icon_if_exists(icon_path, icon_applier or self._qapp.setWindowIcon)
        self._windows: list[MainWindow] = []
        self._executor = PreviewExecutor(parent=qapp)
        self._ipc = ipc if ipc is not None else SingleInstance()
        self._is_primary = self._ipc.become_server(self._on_ipc_paths)
        self._ipc_closed = False

    def _on_ipc_paths(self, paths: list[str]) -> None:
        try:
            append_smoke_batch(paths)
        except OSError as exc:
            print(f"Reader smoke batch log failed during IPC: {exc}", file=sys.stderr)
            self._qapp.exit(2)
            return
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
        self._place_window(window)
        window.show()
        return window

    def _place_window(self, window: MainWindow) -> None:
        offset = max(0, len(self._windows) - 1) * 32
        window.center_on_screen(offset)

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
