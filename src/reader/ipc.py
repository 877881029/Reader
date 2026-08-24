from __future__ import annotations

import json
import os
import re
import struct
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "Reader.SingleInstance.v1"
LOCK_DIR = Path(tempfile.gettempdir()) / "reader-single-instance-locks"
_LOCK_TIMEOUT_MS = 0
_CONNECT_TIMEOUT_MS = 1000
_CONNECT_ATTEMPTS = 5
_WRITE_TIMEOUT_MS = 1000
_READ_SLICE_TIMEOUT_MS = 100
_READ_TOTAL_TIMEOUT_MS = 5000
_HEADER_SIZE = 4
SEND_CHUNK_BYTES: int | None = None
POST_SEND_EVENT_PUMPS = 3
MAX_CONSECUTIVE_ZERO_WRITES = 3


def server_name() -> str:
    namespace = os.environ.get("READER_IPC_NAMESPACE", "").strip()
    if not namespace:
        return SERVER_NAME
    safe_namespace = re.sub(r"[^A-Za-z0-9_.-]", "_", namespace)
    return f"{SERVER_NAME}.{safe_namespace}"


class SingleInstance:
    def __init__(self) -> None:
        self._server_name = server_name()
        self._server: QLocalServer | None = None
        self._lock: QLockFile | None = None
        self._on_paths: Callable[[list[str]], None] | None = None
        self._draining = False

    def become_server(self, on_paths: Callable[[list[str]], None]) -> bool:
        if not self._acquire_lock():
            return False

        server = QLocalServer()
        if server.listen(self._server_name):
            self._adopt_server(server, on_paths)
            self._pump_events()
            return True

        QLocalServer.removeServer(self._server_name)
        if not server.listen(self._server_name):
            self._release_lock()
            return False

        self._adopt_server(server, on_paths)
        self._pump_events()
        return True

    def _adopt_server(self, server: QLocalServer, on_paths: Callable[[list[str]], None]) -> None:
        self._server = server
        self._on_paths = on_paths
        server.newConnection.connect(self._read_connection)

    @staticmethod
    def _pump_events() -> None:
        app = QCoreApplication.instance()
        if app is not None:
            app.processEvents()

    def _acquire_lock(self) -> bool:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        lock = QLockFile(str(self._lock_path()))
        lock.setStaleLockTime(0)
        if not lock.tryLock(_LOCK_TIMEOUT_MS):
            return False
        self._lock = lock
        return True

    def _release_lock(self) -> None:
        if self._lock is not None:
            self._lock.unlock()
            self._lock = None

    def _lock_path(self) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", self._server_name)
        return LOCK_DIR / f"{safe_name}.lock"

    def _read_connection(self) -> None:
        if self._server is None or self._draining:
            return
        self._draining = True
        try:
            while True:
                sock = self._server.nextPendingConnection()
                if sock is None:
                    return
                self._handle_sock(sock)
        finally:
            self._draining = False

    def process_once(self) -> None:
        if self._server is None:
            return
        if not self._server.waitForNewConnection(_CONNECT_TIMEOUT_MS):
            return
        self._read_connection()

    def _read_exact(self, sock: QLocalSocket, size: int) -> bytes | None:
        data = bytearray()
        deadline = time.monotonic() + (_READ_TOTAL_TIMEOUT_MS / 1000.0)

        while len(data) < size:
            chunk = bytes(sock.read(size - len(data)))
            if chunk:
                data.extend(chunk)
                continue

            now = time.monotonic()
            if now >= deadline:
                return None

            wait_ms = int(min(_READ_SLICE_TIMEOUT_MS, max((deadline - now) * 1000.0, 1.0)))
            if sock.waitForReadyRead(wait_ms):
                continue

            is_unconnected = False
            if hasattr(sock, "state") and hasattr(sock, "UnconnectedState"):
                is_unconnected = sock.state() == sock.UnconnectedState
            if is_unconnected:
                pending = bytes(sock.readAll())
                if pending:
                    data.extend(pending)
                    if len(data) >= size:
                        break
                if sock.bytesAvailable() == 0:
                    return None
                continue

        return bytes(data)

    def _handle_sock(self, sock: QLocalSocket) -> None:
        try:
            header = self._read_exact(sock, _HEADER_SIZE)
            if header is None:
                return
            payload_len = struct.unpack(">I", header)[0]
            payload = self._read_exact(sock, payload_len)
            if payload is None:
                return
            decoded = json.loads(payload.decode("utf-8"))
            if isinstance(decoded, list):
                paths = [str(item) for item in decoded]
                if self._on_paths is not None:
                    self._on_paths(paths)
        finally:
            sock.disconnectFromServer()

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            QLocalServer.removeServer(self._server_name)
            self._server = None
        self._on_paths = None
        self._release_lock()

    @staticmethod
    def send_paths(paths: list[str]) -> bool:
        sock: QLocalSocket | None = None
        target_server = server_name()
        for attempt in range(_CONNECT_ATTEMPTS):
            SingleInstance._pump_events()
            candidate = QLocalSocket()
            candidate.connectToServer(target_server)
            if candidate.waitForConnected(_CONNECT_TIMEOUT_MS):
                sock = candidate
                break
            candidate.disconnectFromServer()
            if attempt + 1 < _CONNECT_ATTEMPTS:
                SingleInstance._pump_events()
                time.sleep(0.025 * (attempt + 1))
        if sock is None:
            return False

        payload = json.dumps([str(p) for p in paths], ensure_ascii=False).encode("utf-8")
        frame = struct.pack(">I", len(payload)) + payload

        total_written = 0
        consecutive_zero_writes = 0
        while total_written < len(frame):
            remaining = frame[total_written:]
            if SEND_CHUNK_BYTES is not None and SEND_CHUNK_BYTES > 0:
                remaining = remaining[:SEND_CHUNK_BYTES]
            written = sock.write(remaining)
            if written < 0:
                sock.disconnectFromServer()
                return False
            if written == 0:
                consecutive_zero_writes += 1
                if consecutive_zero_writes > MAX_CONSECUTIVE_ZERO_WRITES:
                    sock.disconnectFromServer()
                    return False
                if not sock.waitForBytesWritten(_WRITE_TIMEOUT_MS):
                    sock.disconnectFromServer()
                    return False
                SingleInstance._pump_events()
                continue
            consecutive_zero_writes = 0
            total_written += written

        if hasattr(sock, "flush"):
            sock.flush()
        for _ in range(POST_SEND_EVENT_PUMPS):
            if sock.bytesToWrite() == 0:
                sock.disconnectFromServer()
                return True
            sock.waitForBytesWritten(_WRITE_TIMEOUT_MS)
            SingleInstance._pump_events()
            if sock.bytesToWrite() == 0:
                sock.disconnectFromServer()
                return True
        sock.disconnectFromServer()
        return False
