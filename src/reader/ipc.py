from __future__ import annotations

import json
from collections.abc import Callable

from PySide6.QtNetwork import QLocalServer, QLocalSocket

SERVER_NAME = "Reader.SingleInstance.v1"
_CONNECT_TIMEOUT_MS = 500
_READ_TIMEOUT_MS = 500
_MAX_READ_SPINS = 20


class SingleInstance:
    def __init__(self) -> None:
        self._server: QLocalServer | None = None
        self._on_paths: Callable[[list[str]], None] | None = None

    def become_server(self, on_paths: Callable[[list[str]], None]) -> bool:
        if self._can_connect_existing_server():
            return False

        server = QLocalServer()
        if server.listen(SERVER_NAME):
            self._adopt_server(server, on_paths)
            return True

        QLocalServer.removeServer(SERVER_NAME)
        if not server.listen(SERVER_NAME):
            return False

        self._adopt_server(server, on_paths)
        return True

    def _adopt_server(self, server: QLocalServer, on_paths: Callable[[list[str]], None]) -> None:
        self._server = server
        self._on_paths = on_paths
        server.newConnection.connect(self._read_connection)

    def _can_connect_existing_server(self) -> bool:
        sock = QLocalSocket()
        sock.connectToServer(SERVER_NAME)
        connected = sock.waitForConnected(_CONNECT_TIMEOUT_MS)
        if connected:
            sock.disconnectFromServer()
        return connected

    def _read_connection(self) -> None:
        if self._server is None:
            return
        while True:
            sock = self._server.nextPendingConnection()
            if sock is None:
                return
            self._handle_sock(sock)

    def process_once(self) -> None:
        if self._server is None:
            return
        if not self._server.waitForNewConnection(_CONNECT_TIMEOUT_MS):
            return
        self._read_connection()

    def _read_all_bytes(self, sock: QLocalSocket) -> bytes:
        data = bytearray()
        for _ in range(_MAX_READ_SPINS):
            chunk = bytes(sock.readAll())
            if chunk:
                data.extend(chunk)
            if sock.waitForReadyRead(_READ_TIMEOUT_MS):
                continue
            break
        tail = bytes(sock.readAll())
        if tail:
            data.extend(tail)
        return bytes(data)

    def _handle_sock(self, sock: QLocalSocket) -> None:
        try:
            payload = self._read_all_bytes(sock)
            if not payload:
                return
            decoded = json.loads(payload.decode("utf-8"))
            if isinstance(decoded, list):
                paths = [str(item) for item in decoded]
                if self._on_paths is not None:
                    self._on_paths(paths)
        finally:
            sock.disconnectFromServer()

    def close(self) -> None:
        if self._server is None:
            return
        self._server.close()
        QLocalServer.removeServer(SERVER_NAME)
        self._server = None
        self._on_paths = None

    @staticmethod
    def send_paths(paths: list[str]) -> bool:
        sock = QLocalSocket()
        sock.connectToServer(SERVER_NAME)
        if not sock.waitForConnected(_CONNECT_TIMEOUT_MS):
            return False
        payload = json.dumps([str(p) for p in paths], ensure_ascii=False).encode("utf-8")
        total_written = 0
        while total_written < len(payload):
            written = sock.write(payload[total_written:])
            if written < 0:
                sock.disconnectFromServer()
                return False
            if written == 0 and not sock.waitForBytesWritten(_CONNECT_TIMEOUT_MS):
                sock.disconnectFromServer()
                return False
            total_written += written
        sock.flush()
        if sock.bytesToWrite() > 0 and not sock.waitForBytesWritten(_CONNECT_TIMEOUT_MS):
            sock.disconnectFromServer()
            return False
        sock.disconnectFromServer()
        return True
