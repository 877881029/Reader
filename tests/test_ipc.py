from __future__ import annotations

import json
import struct
import sys
import time
import uuid
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication
import reader.ipc as ipc_module
from reader.ipc import SERVER_NAME, SingleInstance

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)


def test_server_name_is_v1(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("READER_IPC_NAMESPACE", raising=False)

    assert SERVER_NAME == "Reader.SingleInstance.v1"
    assert ipc_module.server_name() == SERVER_NAME


def test_server_name_namespace_override_is_isolated(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("READER_IPC_NAMESPACE", "smoke-123")

    assert ipc_module.server_name() == f"{SERVER_NAME}.smoke-123"
    instance = SingleInstance()
    assert instance._server_name == f"{SERVER_NAME}.smoke-123"
    assert instance._lock_path().name == f"{SERVER_NAME}.smoke-123.lock"


def _wait_until(predicate, timeout_s: float = 5.0) -> bool:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        _app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def _patch_unique_server(monkeypatch: pytest.MonkeyPatch, tmp_path):
    name = f"{SERVER_NAME}.{uuid.uuid4().hex}"
    monkeypatch.setattr(ipc_module, "SERVER_NAME", name)
    monkeypatch.setattr(ipc_module, "LOCK_DIR", tmp_path)
    return name


def test_send_paths_waits_until_bytes_to_write_empty(monkeypatch: pytest.MonkeyPatch):
    class FakeSocket:
        def __init__(self) -> None:
            self.connected = False
            self.write_calls: list[bytes] = []
            self._bytes_pending = [9, 4, 1, 0]
            self.wait_calls = 0

        def connectToServer(self, _name: str) -> None:
            self.connected = True

        def waitForConnected(self, _ms: int) -> bool:
            return self.connected

        def write(self, data: bytes) -> int:
            self.write_calls.append(bytes(data))
            return len(data)

        def flush(self) -> None:
            return None

        def bytesToWrite(self) -> int:
            if self.wait_calls >= len(self._bytes_pending):
                return 0
            return self._bytes_pending[self.wait_calls]

        def waitForBytesWritten(self, _ms: int) -> bool:
            self.wait_calls += 1
            return True

        def disconnectFromServer(self) -> None:
            self.connected = False

    created: list[FakeSocket] = []

    def fake_socket_factory() -> FakeSocket:
        sock = FakeSocket()
        created.append(sock)
        return sock

    monkeypatch.setattr(ipc_module, "QLocalSocket", fake_socket_factory)

    payload = ["C:/tmp/a.md"]
    assert SingleInstance.send_paths(payload) is True
    assert len(created) == 1
    frame = b"".join(created[0].write_calls)
    payload_len = struct.unpack(">I", frame[:4])[0]
    decoded = json.loads(frame[4 : 4 + payload_len].decode("utf-8"))
    assert decoded == payload
    assert created[0].wait_calls >= 3


def test_send_paths_retries_transient_connect_failure(monkeypatch: pytest.MonkeyPatch):
    class FakeSocket:
        attempts = 0

        def __init__(self) -> None:
            FakeSocket.attempts += 1
            self.connected = FakeSocket.attempts >= 2
            self.frame = bytearray()

        def connectToServer(self, _name: str) -> None:
            return None

        def waitForConnected(self, _ms: int) -> bool:
            return self.connected

        def write(self, data: bytes) -> int:
            self.frame.extend(data)
            return len(data)

        def bytesToWrite(self) -> int:
            return 0

        def disconnectFromServer(self) -> None:
            return None

    monkeypatch.setattr(ipc_module, "QLocalSocket", FakeSocket)

    assert SingleInstance.send_paths(["C:/tmp/retry.md"]) is True
    assert FakeSocket.attempts == 2


def test_rejects_active_instance_without_remove(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)

    class FakeLock:
        def __init__(self, _path: str) -> None:
            pass

        def setStaleLockTime(self, _ms: int) -> None:
            return None

        def tryLock(self, _ms: int) -> bool:
            return False

        def unlock(self) -> None:
            return None

    class FakeServer:
        listen_calls = 0

        def __init__(self) -> None:
            self.newConnection = type("S", (), {"connect": lambda *_: None})()

        def listen(self, _name: str) -> bool:
            FakeServer.listen_calls += 1
            return True

    removed: list[str] = []
    monkeypatch.setattr(ipc_module, "QLockFile", FakeLock)
    monkeypatch.setattr(ipc_module, "QLocalServer", FakeServer)
    monkeypatch.setattr(FakeServer, "removeServer", staticmethod(lambda name: removed.append(name)), raising=False)

    inst = SingleInstance()
    assert inst.become_server(lambda _paths: None) is False
    assert FakeServer.listen_calls == 0
    assert removed == []


def test_e2e_paths_unicode_and_multi(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(lambda paths: seen.append(paths)) is True
        payload = ["C:/tmp/a.md", "D:/文档/二号.pptx", "E:/emoji/🙂.md"]
        assert _wait_until(lambda: SingleInstance.send_paths(payload) is True)
        assert _wait_until(lambda: len(seen) == 1)
        assert seen == [payload]
    finally:
        inst.close()


def test_e2e_empty_list(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(lambda paths: seen.append(paths)) is True
        assert _wait_until(lambda: SingleInstance.send_paths([]) is True)
        assert _wait_until(lambda: len(seen) == 1)
        assert seen == [[]]
    finally:
        inst.close()


def test_e2e_chunked_frame(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    monkeypatch.setattr(ipc_module, "SEND_CHUNK_BYTES", 3)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(lambda paths: seen.append(paths)) is True
        payload = ["C:/tmp/one.md", "C:/tmp/two.md", "D:/unicode/空.docx"]
        assert _wait_until(lambda: SingleInstance.send_paths(payload) is True)
        assert _wait_until(lambda: len(seen) == 1)
        assert seen == [payload]
    finally:
        inst.close()


def test_e2e_second_instance_not_hijack(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    seen: list[list[str]] = []
    a = SingleInstance()
    b = SingleInstance()
    try:
        assert a.become_server(lambda paths: seen.append(paths)) is True
        assert b.become_server(lambda _paths: None) is False
        assert _wait_until(lambda: SingleInstance.send_paths(["C:/tmp/main.md"]) is True)
        assert _wait_until(lambda: len(seen) == 1)
        assert seen == [["C:/tmp/main.md"]]
    finally:
        b.close()
        a.close()


def test_process_once_and_signal_do_not_double_consume(monkeypatch: pytest.MonkeyPatch, tmp_path):
    _patch_unique_server(monkeypatch, tmp_path)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(lambda paths: seen.append(paths)) is True
        assert SingleInstance.send_paths(["C:/tmp/once.md"]) is True
        assert _wait_until(lambda: len(seen) == 1)
        inst.process_once()
        _app.processEvents()
        assert seen == [["C:/tmp/once.md"]]
    finally:
        inst.close()


def test_become_server_cleans_stale_endpoint_once(monkeypatch: pytest.MonkeyPatch):
    class FakeSignal:
        def connect(self, _callback: Any) -> None:
            return None

    class FakeLock:
        locked = False

        def __init__(self, _path: str) -> None:
            pass

        def setStaleLockTime(self, _ms: int) -> None:
            return None

        def tryLock(self, _ms: int) -> bool:
            if FakeLock.locked:
                return False
            FakeLock.locked = True
            return True

        def unlock(self) -> None:
            FakeLock.locked = False

    class FakeServer:
        listen_calls = 0

        def __init__(self) -> None:
            self.newConnection = FakeSignal()

        def listen(self, _name: str) -> bool:
            FakeServer.listen_calls += 1
            return FakeServer.listen_calls >= 2

        def close(self) -> None:
            return None

    removed: list[str] = []
    monkeypatch.setattr(ipc_module, "QLockFile", FakeLock)
    monkeypatch.setattr(ipc_module, "QLocalServer", FakeServer)
    monkeypatch.setattr(FakeServer, "removeServer", staticmethod(lambda name: removed.append(name)), raising=False)

    inst = SingleInstance()
    assert inst.become_server(lambda _paths: None) is True
    assert FakeServer.listen_calls == 2
    assert removed == [SERVER_NAME]
    inst.close()
