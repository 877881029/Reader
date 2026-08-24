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


@pytest.fixture(autouse=True)
def _clear_ipc_namespace(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("READER_IPC_NAMESPACE", raising=False)


class _DrainSocket:
    def __init__(
        self,
        pending: int,
        pending_after_wait: list[int],
        wait_results: list[bool] | None = None,
        ack: bytes = b"ACK",
    ) -> None:
        self.pending = pending
        self.pending_after_wait = list(pending_after_wait)
        self.wait_results = list(wait_results) if wait_results is not None else [True]
        self.wait_calls = 0
        self.disconnected_with_pending: bool | None = None
        self.ack = bytearray(ack)
        self.ready_read_calls = 0
        self.read_calls = 0

    def connectToServer(self, _name: str) -> None:
        return None

    def waitForConnected(self, _ms: int) -> bool:
        return True

    def write(self, data: bytes) -> int:
        return len(data)

    def bytesToWrite(self) -> int:
        return self.pending

    def flush(self) -> None:
        return None

    def waitForBytesWritten(self, _ms: int) -> bool:
        index = self.wait_calls
        self.wait_calls += 1
        if index < len(self.pending_after_wait):
            self.pending = self.pending_after_wait[index]
        if index < len(self.wait_results):
            return self.wait_results[index]
        return self.wait_results[-1]

    def disconnectFromServer(self) -> None:
        self.disconnected_with_pending = self.pending > 0

    def waitForReadyRead(self, _ms: int) -> bool:
        self.ready_read_calls += 1
        return bool(self.ack)

    def read(self, size: int) -> bytes:
        self.read_calls += 1
        chunk = bytes(self.ack[:size])
        del self.ack[:size]
        return chunk


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
            self._bytes_pending = [9, 0]
            self.wait_calls = 0
            self.ack = bytearray(b"ACK")

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

        def read(self, size: int) -> bytes:
            chunk = bytes(self.ack[:size])
            del self.ack[:size]
            return chunk

        def waitForReadyRead(self, _ms: int) -> bool:
            return bool(self.ack)

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
    assert created[0].wait_calls == 1


def test_send_paths_returns_false_when_flush_queue_stays_pending(
    monkeypatch: pytest.MonkeyPatch,
):
    sock = _DrainSocket(pending=7, pending_after_wait=[])
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert SingleInstance.send_paths(["C:/tmp/stuck.md"]) is False
    assert sock.wait_calls == ipc_module.POST_SEND_EVENT_PUMPS
    assert sock.disconnected_with_pending is True


def test_send_paths_succeeds_when_failed_wait_pumps_queue_empty(
    monkeypatch: pytest.MonkeyPatch,
):
    sock = _DrainSocket(
        pending=5,
        pending_after_wait=[5],
        wait_results=[False],
    )
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)
    monkeypatch.setattr(
        SingleInstance,
        "_pump_events",
        staticmethod(
            lambda: setattr(sock, "pending", 0) if sock.wait_calls > 0 else None
        ),
    )

    assert SingleInstance.send_paths(["C:/tmp/late-empty.md"]) is True
    assert sock.wait_calls == 1
    assert sock.disconnected_with_pending is False


def test_send_paths_drains_normal_multi_round_flush_queue(
    monkeypatch: pytest.MonkeyPatch,
):
    sock = _DrainSocket(pending=8, pending_after_wait=[3, 0])
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert SingleInstance.send_paths(["C:/tmp/multi-round.md"]) is True
    assert sock.wait_calls == 2
    assert sock.disconnected_with_pending is False


def test_send_paths_waits_for_application_ack(monkeypatch: pytest.MonkeyPatch):
    sock = _DrainSocket(pending=0, pending_after_wait=[], ack=b"ACK")
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert SingleInstance.send_paths(["C:/tmp/acked.md"]) is True
    assert sock.read_calls >= 1


def test_send_paths_returns_false_without_application_ack(
    monkeypatch: pytest.MonkeyPatch,
):
    sock = _DrainSocket(pending=0, pending_after_wait=[], ack=b"")
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert SingleInstance.send_paths(["C:/tmp/no-ack.md"]) is False


def test_server_acks_only_after_successful_callback():
    payload = json.dumps(["C:/tmp/success.md"]).encode("utf-8")

    class ServerSocket:
        def __init__(self) -> None:
            self.incoming = bytearray(struct.pack(">I", len(payload)) + payload)
            self.writes: list[bytes] = []
            self.disconnected = False

        def read(self, size: int) -> bytes:
            chunk = bytes(self.incoming[:size])
            del self.incoming[:size]
            return chunk

        def write(self, data: bytes) -> int:
            self.writes.append(bytes(data))
            return len(data)

        def bytesToWrite(self) -> int:
            return 0

        def disconnectFromServer(self) -> None:
            self.disconnected = True

    seen: list[list[str]] = []
    sock = ServerSocket()
    instance = SingleInstance()
    instance._on_paths = seen.append

    instance._handle_sock(sock)

    assert seen == [["C:/tmp/success.md"]]
    assert b"".join(sock.writes) == b"ACK"
    assert sock.disconnected is True


def test_server_callback_exception_sends_no_ack():
    payload = json.dumps(["C:/tmp/fail.md"]).encode("utf-8")

    class ServerSocket:
        def __init__(self) -> None:
            self.incoming = bytearray(struct.pack(">I", len(payload)) + payload)
            self.writes: list[bytes] = []
            self.disconnected = False

        def read(self, size: int) -> bytes:
            chunk = bytes(self.incoming[:size])
            del self.incoming[:size]
            return chunk

        def write(self, data: bytes) -> int:
            self.writes.append(bytes(data))
            return len(data)

        def disconnectFromServer(self) -> None:
            self.disconnected = True

    sock = ServerSocket()
    instance = SingleInstance()
    instance._on_paths = lambda _paths: (_ for _ in ()).throw(RuntimeError("boom"))

    instance._handle_sock(sock)

    assert sock.writes == []
    assert sock.disconnected is True


def test_server_ack_drain_is_bounded_for_gui_thread():
    class StuckAckSocket:
        def __init__(self) -> None:
            self.wait_timeouts: list[int] = []

        def write(self, data: bytes) -> int:
            return len(data)

        def bytesToWrite(self) -> int:
            return len(b"ACK")

        def waitForBytesWritten(self, timeout_ms: int) -> bool:
            self.wait_timeouts.append(timeout_ms)
            return True

    sock = StuckAckSocket()

    assert SingleInstance._send_ack(sock) is False
    assert len(sock.wait_timeouts) == ipc_module.POST_SEND_EVENT_PUMPS
    assert max(sock.wait_timeouts) <= 100


def test_send_paths_bounds_repeated_zero_byte_writes(
    monkeypatch: pytest.MonkeyPatch,
):
    class ZeroWriteSocket(_DrainSocket):
        def __init__(self) -> None:
            super().__init__(pending=0, pending_after_wait=[])
            self.write_calls = 0

        def write(self, _data: bytes) -> int:
            self.write_calls += 1
            return 0 if self.write_calls <= 100 else -1

        def waitForBytesWritten(self, _ms: int) -> bool:
            return True

    sock = ZeroWriteSocket()
    monkeypatch.setattr(ipc_module, "QLocalSocket", lambda: sock)

    assert SingleInstance.send_paths(["C:/tmp/zero-write.md"]) is False
    assert sock.write_calls <= 4
    assert sock.disconnected_with_pending is False


def test_send_paths_retries_transient_connect_failure(monkeypatch: pytest.MonkeyPatch):
    class FakeSocket:
        attempts = 0

        def __init__(self) -> None:
            FakeSocket.attempts += 1
            self.connected = FakeSocket.attempts >= 2
            self.frame = bytearray()
            self.ack = bytearray(b"ACK")

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

        def read(self, size: int) -> bytes:
            chunk = bytes(self.ack[:size])
            del self.ack[:size]
            return chunk

        def waitForReadyRead(self, _ms: int) -> bool:
            return bool(self.ack)

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
    lock_path = ipc_module.LOCK_DIR / f"{SERVER_NAME}.{namespace}.lock"
    start_event = context.Event()
    result_queue = context.Queue()
    large_unicode = "长" * 80_000
    payloads = [
        [
            f"C:/launch/{index}-🙂-{large_unicode}.md",
            f"D:/launch/{index}-二.pptx",
        ]
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
    started_processes = []
    try:
        for process in processes:
            process.start()
            started_processes.append(process)
        start_event.set()

        messages = [
            result_queue.get(timeout=20.0) for _ in range(len(payloads) * 2)
        ]
        for process in started_processes:
            process.join(timeout=20.0)
            assert process.exitcode == 0
    finally:
        for process in started_processes:
            if process.is_alive():
                process.terminate()
            process.join(timeout=5.0)
            if process.is_alive():
                process.kill()
                process.join(timeout=5.0)
        try:
            result_queue.cancel_join_thread()
            result_queue.close()
        finally:
            lock_path.unlink(missing_ok=True)

    assert len(messages) == 12
    assert not lock_path.exists()
    roles = [message for message in messages if message[0] == "role"]
    sent = [message for message in messages if message[0] == "sent"]
    deliveries = [message for message in messages if message[0] == "seen"]
    assert {message[0] for message in messages} == {"role", "sent", "seen"}
    assert len(roles) == 6
    assert len(sent) == 5
    assert len(deliveries) == 1
    assert {message[1] for message in roles} == set(range(6))
    assert {message[1] for message in sent} | {deliveries[0][1]} == set(range(6))
    assert sum(bool(message[2]) for message in roles) == 1
    assert all(message[2] is True for message in sent)
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
