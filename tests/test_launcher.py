from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QLocalServer

import reader.launcher as launcher
from reader.ipc import SingleInstance, server_name

_app = QCoreApplication.instance() or QCoreApplication(sys.argv)

_FORWARD_SCRIPT = (
    "import json, sys\n"
    "from reader import launcher\n"
    "result = launcher.forward_paths(json.loads(sys.argv[1]), ack_timeout_s=float(sys.argv[2]))\n"
    "print(json.dumps({'result': result, 'qt': 'PySide6' in sys.modules}))\n"
)


@pytest.fixture()
def namespace(monkeypatch: pytest.MonkeyPatch) -> str:
    value = f"launcher-{uuid.uuid4().hex}"
    monkeypatch.setenv("READER_IPC_NAMESPACE", value)
    return value


def _run_forward(paths: list[str], ack_timeout_s: float = 5.0) -> dict:
    proc = subprocess.Popen(
        [sys.executable, "-c", _FORWARD_SCRIPT, json.dumps(paths), str(ack_timeout_s)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    deadline = time.monotonic() + 30.0
    while proc.poll() is None and time.monotonic() < deadline:
        _app.processEvents()
        time.sleep(0.005)
    out, err = proc.communicate(timeout=5)
    assert proc.returncode == 0, err
    return json.loads(out.strip().splitlines()[-1])


def test_pipe_path_matches_qt_server_name(namespace: str):
    assert launcher.pipe_path() == "\\\\.\\pipe\\" + server_name()
    assert namespace in launcher.pipe_path()


def test_forward_delivers_absolute_paths_to_running_instance_without_qt(namespace: str, tmp_path):
    seen: list[list[str]] = []
    inst = SingleInstance()
    try:
        assert inst.become_server(seen.append) is True
        paths = [str(tmp_path / "一.txt"), str(tmp_path / "🙂 two.md")]
        report = _run_forward(paths)
    finally:
        inst.close()

    assert report == {"result": launcher.DELIVERED, "qt": False}
    assert seen == [paths]


def test_forward_reports_no_server_quickly(namespace: str):
    started = time.monotonic()
    assert launcher.forward_paths(["C:/x.txt"]) == launcher.NO_SERVER
    assert time.monotonic() - started < 1.0


def test_forward_reports_failure_when_server_never_acknowledges(namespace: str):
    server = QLocalServer()
    assert server.listen(server_name())
    try:
        report = _run_forward(["C:/x.txt"], ack_timeout_s=0.5)
    finally:
        server.close()

    assert report["result"] == launcher.FAILED


def test_main_forwards_absolute_paths_and_skips_full_app(monkeypatch, tmp_path):
    sent: list[list[str]] = []
    monkeypatch.setattr(launcher, "forward_paths", lambda paths: sent.append(paths) or launcher.DELIVERED)
    monkeypatch.setattr(launcher, "_run_full_app", lambda argv: pytest.fail("full app started"))
    monkeypatch.chdir(tmp_path)

    assert launcher.main(["Reader.exe", "a.txt"]) == 0
    assert sent == [[str(tmp_path / "a.txt")]]


def test_main_starts_full_app_when_no_instance_runs(monkeypatch):
    started: list[list[str]] = []
    monkeypatch.setattr(launcher, "forward_paths", lambda paths: launcher.NO_SERVER)
    monkeypatch.setattr(launcher, "_run_full_app", lambda argv: started.append(argv) or 7)

    assert launcher.main(["Reader.exe", "C:/a.txt"]) == 7
    assert started == [["Reader.exe", "C:/a.txt"]]


def test_main_does_not_restart_when_delivery_failed(monkeypatch):
    monkeypatch.setattr(launcher, "forward_paths", lambda paths: launcher.FAILED)
    monkeypatch.setattr(launcher, "_run_full_app", lambda argv: pytest.fail("full app started"))

    assert launcher.main(["Reader.exe", "C:/a.txt"]) == 2


def test_main_passes_option_commands_straight_to_full_app(monkeypatch):
    started: list[list[str]] = []
    monkeypatch.setattr(launcher, "forward_paths", lambda paths: pytest.fail("forwarded"))
    monkeypatch.setattr(launcher, "_run_full_app", lambda argv: started.append(argv) or 0)

    assert launcher.main(["Reader.exe", "--pty-selftest", "out.json"]) == 0
    assert started == [["Reader.exe", "--pty-selftest", "out.json"]]


def test_launcher_module_does_not_import_qt():
    code = "import sys, reader.launcher; print('PySide6' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"


def test_packaged_entry_point_is_launcher():
    root = Path(__file__).resolve().parents[1]
    spec = (root / "reader.spec").read_text(encoding="utf-8")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[str(ROOT / 'src/reader/launcher.py')]" in spec
    assert 'reader = "reader.launcher:main"' in pyproject
