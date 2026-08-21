from __future__ import annotations

import json
import sys
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication

import reader.ipc as ipc_module
from reader.ipc import SERVER_NAME, SingleInstance

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)


def test_server_name_is_v1():
    assert SERVER_NAME == "Reader.SingleInstance.v1"


def test_existing_server_detected_without_remove_server(monkeypatch: pytest.MonkeyPatch):
    class FakeSignal:
        def connect(self, _callback: Any) -> None:
            return None

    class FakeServer:
        listen_calls = 0

        def __init__(self) -> None:
            self.newConnection = FakeSignal()

        def listen(self, _name: str) -> bool:
            FakeServer.listen_calls += 1
            return True

    class FakeSocket:
        connect_calls = 0

        def connectToServer(self, _name: str) -> None:
            FakeSocket.connect_calls += 1

        def waitForConnected(self, _ms: int) -> bool:
            return True

        def disconnectFromServer(self) -> None:
            return None

    removed: list[str] = []

    def fake_remove(name: str) -> bool:
        removed.append(name)
        return True

    monkeypatch.setattr(ipc_module, "QLocalServer", FakeServer)
    monkeypatch.setattr(ipc_module, "QLocalSocket", FakeSocket)
    monkeypatch.setattr(FakeServer, "removeServer", staticmethod(fake_remove), raising=False)

    inst = SingleInstance()
    assert inst.become_server(lambda _paths: None) is False
    assert FakeSocket.connect_calls == 1
    assert FakeServer.listen_calls == 0
    assert removed == []


def test_send_paths_transfers_json_list(monkeypatch: pytest.MonkeyPatch):
    class FakeSocket:
        def __init__(self) -> None:
            self.connected = False
            self.sent = bytearray()
            self._bytes_to_write = 0

        def connectToServer(self, _name: str) -> None:
            self.connected = True

        def waitForConnected(self, _ms: int) -> bool:
            return self.connected

        def write(self, data: bytes) -> int:
            self.sent.extend(data)
            self._bytes_to_write = 0
            return len(data)

        def flush(self) -> None:
            return None

        def bytesToWrite(self) -> int:
            return self._bytes_to_write

        def waitForBytesWritten(self, _ms: int) -> bool:
            return True

        def disconnectFromServer(self) -> None:
            self.connected = False

    created: list[FakeSocket] = []

    def fake_socket_factory() -> FakeSocket:
        sock = FakeSocket()
        created.append(sock)
        return sock

    monkeypatch.setattr(ipc_module, "QLocalSocket", fake_socket_factory)

    payload = [f"C:/tmp/{i:05d}.md" for i in range(2000)]
    assert SingleInstance.send_paths(payload) is True
    assert len(created) == 1
    decoded = json.loads(created[0].sent.decode("utf-8"))
    assert decoded == payload


def test_read_connection_waits_for_complete_json(monkeypatch: pytest.MonkeyPatch):
    class FakeSocket:
        def __init__(self, chunks: list[bytes]) -> None:
            self._chunks = chunks
            self._idx = 0
            self.disconnected = False

        def readAll(self) -> bytes:
            if self._idx >= len(self._chunks):
                return b""
            chunk = self._chunks[self._idx]
            self._idx += 1
            return chunk

        def waitForReadyRead(self, _ms: int) -> bool:
            return self._idx < len(self._chunks)

        def disconnectFromServer(self) -> None:
            self.disconnected = True

    seen: list[list[str]] = []
    inst = SingleInstance()
    inst._on_paths = lambda paths: seen.append(paths)  # noqa: SLF001
    payload = json.dumps(["C:/tmp/a.md", "C:/tmp/b.md"]).encode("utf-8")
    chunks = [payload[:7], payload[7:13], payload[13:]]
    sock = FakeSocket(chunks)

    inst._handle_sock(sock)  # noqa: SLF001

    assert seen == [["C:/tmp/a.md", "C:/tmp/b.md"]]
    assert sock.disconnected is True


def test_become_server_cleans_stale_endpoint_once(monkeypatch: pytest.MonkeyPatch):
    class FakeSignal:
        def __init__(self) -> None:
            self._callbacks: list[Any] = []

        def connect(self, callback: Any) -> None:
            self._callbacks.append(callback)

    class FakeServer:
        listen_calls = 0

        def __init__(self) -> None:
            self.newConnection = FakeSignal()

        def listen(self, _name: str) -> bool:
            FakeServer.listen_calls += 1
            return FakeServer.listen_calls >= 2

    class FakeSocket:
        connect_calls = 0

        def connectToServer(self, _name: str) -> None:
            FakeSocket.connect_calls += 1

        def waitForConnected(self, _ms: int) -> bool:
            return False

    removed: list[str] = []

    def fake_remove(name: str) -> bool:
        removed.append(name)
        return True

    monkeypatch.setattr(ipc_module, "QLocalServer", FakeServer)
    monkeypatch.setattr(ipc_module, "QLocalSocket", FakeSocket)
    monkeypatch.setattr(FakeServer, "removeServer", staticmethod(fake_remove), raising=False)

    inst = SingleInstance()
    assert inst.become_server(lambda _paths: None) is True
    assert FakeSocket.connect_calls == 1
    assert FakeServer.listen_calls == 2
    assert removed == [SERVER_NAME]
