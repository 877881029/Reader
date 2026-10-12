"""Headless ConPTY check used by the frozen smoke test (``--pty-selftest``)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from reader.terminal.pty_session import DA1_RESPONSE, SHELL_PROFILES

MARKER = "READER_PTY_SELFTEST"
TIMEOUT_SECONDS = 20.0


def run_pty_selftest(output_path: Path) -> int:
    from winpty import PtyProcess

    shell = SHELL_PROFILES["cmd"].argv[0]
    chunks: list[str] = []
    ok = False
    error = ""
    pty = None
    try:
        pty = PtyProcess.spawn([shell], dimensions=(24, 100))

        def reader() -> None:
            while True:
                try:
                    data = pty.read(4096)
                except Exception:
                    return
                if data:
                    chunks.append(data)

        threading.Thread(target=reader, daemon=True).start()
        pty.write(DA1_RESPONSE)
        pty.write(f"echo {MARKER}_%PROCESSOR_ARCHITECTURE%\r")
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if f"{MARKER}_" in "".join(chunks).split("echo", 1)[-1]:
                ok = True
                break
            time.sleep(0.05)
    except Exception as exc:  # report, never crash the smoke harness
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if pty is not None:
            try:
                pty.terminate(force=True)
            except Exception:
                pass
    text = "".join(chunks)
    Path(output_path).write_text(
        json.dumps({"ok": ok, "shell": shell, "tail": text[-400:], "error": error}),
        encoding="utf-8",
    )
    return 0 if ok else 1