from __future__ import annotations

import json
import multiprocessing
import os
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


def _concurrent_launch_worker(
    namespace: str,
    launch_id: int,
    paths: list[str],
    launch_count: int,
    start_event,
    result_queue,
) -> None:
    """Run the IPC portion of __main__ without creating GUI windows."""
    os.environ["READER_IPC_NAMESPACE"] = namespace
    app = QCoreApplication.instance() or QCoreApplication([])
    seen: list[list[str]] = []
    instance = SingleInstance()
    start_event.wait()
    is_primary = instance.become_server(seen.append)
    result_queue.put(("role", launch_id, is_primary))
    try:
        if is_primary:
            deadline = time.monotonic() + 15.0
            seen.append(paths)
            while len(seen) < launch_count and time.monotonic() < deadline:
                app.processEvents()
            result_queue.put(("seen", launch_id, seen))
        else:
            result_queue.put(("sent", launch_id, SingleInstance.send_paths(paths)))
    finally:
        instance.close()


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


def test_send_paths_drains_bytes_queued_by_flush(monkeypatch: pytest.MonkeyPatch):
    class FlushQueuesSocket:
        def __init__(self) -> None:
            self.pending = 0
            self.wait_calls = 0
            self.disconnected_with_pending = False

        def connectToServer(self, _name: str) -> None:
            return None

        def waitForConnected(self, _ms: int) -> bool:
            return True

        def write(self, data: bytes) -> int:
            return len(data)

        def bytesToWrite(self) -> int:
            return self.pending

        def flush(self) -> None:
            self.pending = ipc_module.POST_SEND_EVENT_PUMPS

        def waitForBytesWritten(self, _ms: int) -> bool:
            self.wait_calls += 1
            self.pending -= 1
            return True

        def disconnectFromServer(self) -> None:
            self.disconnected_with_pending = self.pending > 0

    sock = FlushQueuesSocket()
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert ipc_module.POST_SEND_EVENT_PUMPS == 3
    assert SingleInstance.send_paths(["C:/tmp/flush.md"]) is True
    assert sock.wait_calls == ipc_module.POST_SEND_EVENT_PUMPS
    assert sock.disconnected_with_pending is False


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

    sleeps: list[float] = []
    monkeypatch.setattr(ipc_module, "QLocalSocket", FakeSocket)
    monkeypatch.setattr(ipc_module.time, "sleep", sleeps.append)

    assert SingleInstance.send_paths(["C:/tmp/retry.md"]) is True
    assert FakeSocket.attempts == 2
    assert sleeps == [0.025]


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


def test_e2e_rapid_sequential_open_with_launches(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    _patch_unique_server(monkeypatch, tmp_path)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(seen.append) is True
        payloads = [
            [f"C:/tmp/{index}-一.md", f"D:/batch/{index}-二.pptx"]
            for index in range(8)
        ]
        for payload in payloads:
            assert SingleInstance.send_paths(payload) is True
        assert _wait_until(lambda: len(seen) == len(payloads), timeout_s=8.0)
        assert seen == payloads
    finally:
        inst.close()


def test_e2e_large_unicode_frame_is_one_atomic_batch(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    _patch_unique_server(monkeypatch, tmp_path)
    monkeypatch.setattr(ipc_module, "SEND_CHUNK_BYTES", 257)
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(seen.append) is True
        payload = [
            "C:/文档/🙂-" + ("长" * 80_000) + ".md",
            "D:/演示/第二个参数.pptx",
        ]
        assert SingleInstance.send_paths(payload) is True
        assert _wait_until(lambda: len(seen) == 1, timeout_s=8.0)
        assert seen == [payload]
    finally:
        inst.close()


def test_process_launch_race_has_one_primary_and_preserves_batches():
    context = multiprocessing.get_context("spawn")
    namespace = f"process-race-{uuid.uuid4().hex}"
    start_event = context.Event()
    result_queue = context.Queue()
    payloads = [
        [f"C:/launch/{index}-一.md", f"D:/launch/{index}-二.pptx"]
        for index in range(6)
    ]
    processes = [
        context.Process(
            target=_concurrent_launch_worker,
            args=(
                namespace,
                index,
                payload,
                len(payloads),
                start_event,
                result_queue,
            ),
        )
        for index, payload in enumerate(payloads)
    ]
    try:
        for process in processes:
            process.start()
        start_event.set()

        messages = [
            result_queue.get(timeout=20.0) for _ in range(len(payloads) * 2)
        ]
        for process in processes:
            process.join(timeout=20.0)
            assert process.exitcode == 0
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5.0)
        result_queue.close()
        result_queue.join_thread()

    roles = [message for message in messages if message[0] == "role"]
    sent = [message for message in messages if message[0] == "sent"]
    deliveries = [message for message in messages if message[0] == "seen"]
    assert sum(bool(message[2]) for message in roles) == 1
    assert all(message[2] is True for message in sent)
    assert len(deliveries) == 1
    delivered_batches = deliveries[0][2]
    assert sorted(delivered_batches) == sorted(payloads)


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
