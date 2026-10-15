"""Fast entry point.

Forwards the launch to a running Reader over its named pipe using only ctypes, so a
double-click on a file never pays for importing Qt when Reader is already open.
Falls back to the full application when no instance is listening.
"""

from __future__ import annotations

import ctypes
import json
import os
import struct
import sys
import threading
import time
from ctypes import wintypes

from reader.instance_name import server_name

DELIVERED = "delivered"
NO_SERVER = "no-server"
FAILED = "failed"

ACK_FRAME = b"ACK"
_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_ERROR_PIPE_BUSY = 231
_INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value


def pipe_path() -> str:
    return "\\\\.\\pipe\\" + server_name()


def _kernel32():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.WaitNamedPipeW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
    k32.WaitNamedPipeW.restype = wintypes.BOOL
    k32.WriteFile.argtypes = [
        wintypes.HANDLE, wintypes.LPCVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    k32.WriteFile.restype = wintypes.BOOL
    k32.ReadFile.argtypes = [
        wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID,
    ]
    k32.ReadFile.restype = wintypes.BOOL
    k32.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    k32.GetNamedPipeServerProcessId.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL
    return k32


def _open_pipe(k32, path: str, connect_timeout_s: float):
    deadline = time.monotonic() + connect_timeout_s
    while True:
        handle = k32.CreateFileW(
            path, _GENERIC_READ | _GENERIC_WRITE, 0, None, _OPEN_EXISTING, 0, None
        )
        if handle not in (None, _INVALID_HANDLE_VALUE):
            return handle
        remaining_ms = int((deadline - time.monotonic()) * 1000)
        if ctypes.get_last_error() != _ERROR_PIPE_BUSY or remaining_ms <= 0:
            return None
        k32.WaitNamedPipeW(path, max(remaining_ms, 1))


def _allow_server_foreground(k32, handle) -> None:
    pid = wintypes.ULONG(0)
    if k32.GetNamedPipeServerProcessId(handle, ctypes.byref(pid)) and pid.value:
        ctypes.windll.user32.AllowSetForegroundWindow(wintypes.DWORD(pid.value))


def _write_all(k32, handle, data: bytes) -> bool:
    offset = 0
    while offset < len(data):
        chunk = data[offset:]
        written = wintypes.DWORD(0)
        if not k32.WriteFile(handle, chunk, len(chunk), ctypes.byref(written), None):
            return False
        if written.value == 0:
            return False
        offset += written.value
    return True


def _read_ack(k32, handle, timeout_s: float) -> bool | None:
    """True on ACK, False on a clean failure, None if the read is still blocked."""
    # A blocked ReadFile is satisfied the instant the server writes the ACK, before
    # the server can disconnect and discard unread pipe data.
    received = bytearray()

    def reader() -> None:
        buffer = ctypes.create_string_buffer(len(ACK_FRAME))
        while len(received) < len(ACK_FRAME):
            count = wintypes.DWORD(0)
            ok = k32.ReadFile(
                handle, buffer, len(ACK_FRAME) - len(received), ctypes.byref(count), None
            )
            if not ok or count.value == 0:
                return
            received.extend(buffer.raw[: count.value])

    thread = threading.Thread(target=reader, name="reader-launch-ack", daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        return None
    return bytes(received) == ACK_FRAME


def forward_paths(
    paths: list[str], connect_timeout_s: float = 2.0, ack_timeout_s: float = 15.0
) -> str:
    """Send paths to a running Reader.

    Returns NO_SERVER when nothing was delivered (safe to start the full app),
    DELIVERED on ACK, and FAILED when the request may have reached the server.
    """
    if sys.platform != "win32":
        return NO_SERVER
    k32 = _kernel32()
    handle = _open_pipe(k32, pipe_path(), connect_timeout_s)
    if handle is None:
        return NO_SERVER
    _allow_server_foreground(k32, handle)
    payload = json.dumps([str(p) for p in paths], ensure_ascii=False).encode("utf-8")
    if not _write_all(k32, handle, struct.pack(">I", len(payload)) + payload):
        k32.CloseHandle(handle)
        return NO_SERVER
    acked = _read_ack(k32, handle, ack_timeout_s)
    if acked is None:
        # Closing a synchronous handle with a pending read can block; the
        # launcher exits right after, which releases it.
        return FAILED
    k32.CloseHandle(handle)
    return DELIVERED if acked else FAILED


def _run_full_app(argv: list[str]) -> int:
    from reader.__main__ import main as full_main

    return full_main(argv)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if any(arg.startswith("-") for arg in argv[1:]):
        return _run_full_app(argv)
    result = forward_paths([os.path.abspath(arg) for arg in argv[1:]])
    if result == DELIVERED:
        return 0
    if result == FAILED:
        return 2
    return _run_full_app(argv)


if __name__ == "__main__":
    raise SystemExit(main())
