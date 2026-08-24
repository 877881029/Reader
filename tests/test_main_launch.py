import sys

import pytest


def test_launch_target_uses_frozen_executable(monkeypatch):
    import reader.__main__ as main_module

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Reader\Reader.exe")

    assert main_module._association_target() == (r"C:\Reader\Reader.exe", ())


def test_launch_target_uses_python_m_reader_in_development(monkeypatch):
    import reader.__main__ as main_module

    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Python312\python.exe")

    assert main_module._association_target() == (r"C:\Python312\python.exe", ("-m", "reader"))


@pytest.mark.parametrize("value", ["1", "true", "TRUE", " yes ", "On"])
def test_shell_integration_disabled_for_explicit_truthy_values(monkeypatch, value):
    import reader.__main__ as main_module

    monkeypatch.setenv("READER_SKIP_SHELL_INTEGRATION", value)

    assert main_module._shell_integration_disabled() is True


@pytest.mark.parametrize("value", ["", "0", "false", "no", "off", "anything"])
def test_shell_integration_not_disabled_for_other_values(monkeypatch, value):
    import reader.__main__ as main_module

    monkeypatch.setenv("READER_SKIP_SHELL_INTEGRATION", value)

    assert main_module._shell_integration_disabled() is False


def test_primary_launch_records_initial_batch_after_server_ownership(monkeypatch):
    import reader.__main__ as main_module

    events = []

    class FakeQApplication:
        @classmethod
        def instance(cls):
            return None

        def __init__(self, _argv):
            pass

        def exec(self):
            events.append("exec")
            return 0

    class FakeWindow:
        def open_paths(self, paths):
            events.append(("open", paths))

    class FakeReaderApp:
        def __init__(self, _qapp):
            events.append("server")

        def is_primary_instance(self):
            return True

        def new_window(self):
            return FakeWindow()

    monkeypatch.setattr(main_module, "QApplication", FakeQApplication)
    monkeypatch.setattr(main_module, "ReaderApp", FakeReaderApp)
    monkeypatch.setattr(
        main_module,
        "append_smoke_batch",
        lambda paths: events.append(("log", paths)),
        raising=False,
    )
    monkeypatch.setattr(main_module, "_shell_integration_disabled", lambda: True)

    assert main_module.main(["Reader.exe", "one.md", "two.md"]) == 0
    assert events == [
        "server",
        ("log", ["one.md", "two.md"]),
        ("open", ["one.md", "two.md"]),
        "exec",
    ]


def test_secondary_uses_instance_ownership_without_empty_server_probe(monkeypatch):
    import reader.__main__ as main_module

    sent = []

    class FakeQApplication:
        @classmethod
        def instance(cls):
            return None

        def __init__(self, _argv):
            pass

    class FakeReaderApp:
        def __init__(self, _qapp):
            pass

        def is_primary_instance(self):
            return False

    monkeypatch.setattr(
        main_module,
        "_server_running",
        lambda: pytest.fail("empty preflight connection must not be opened"),
        raising=False,
    )
    monkeypatch.setattr(main_module, "QApplication", FakeQApplication)
    monkeypatch.setattr(main_module, "ReaderApp", FakeReaderApp)
    monkeypatch.setattr(
        main_module.SingleInstance,
        "send_paths",
        lambda paths: sent.append(paths) or True,
    )

    assert main_module.main(["Reader.exe", "one.md", "two.md"]) == 0
    assert sent == [["one.md", "two.md"]]


def test_secondary_returns_nonzero_and_reports_failed_delivery(monkeypatch, capsys):
    import reader.__main__ as main_module

    class FakeQApplication:
        @classmethod
        def instance(cls):
            return None

        def __init__(self, _argv):
            pass

    class FakeReaderApp:
        def __init__(self, _qapp):
            pass

        def is_primary_instance(self):
            return False

    monkeypatch.setattr(main_module, "QApplication", FakeQApplication)
    monkeypatch.setattr(main_module, "ReaderApp", FakeReaderApp)
    monkeypatch.setattr(main_module.SingleInstance, "send_paths", lambda _paths: False)

    assert main_module.main(["Reader.exe", "lost.md"]) == 2
    assert "IPC" in capsys.readouterr().err


def _run_primary_with_shell_failure(monkeypatch, *, association_error=False, shortcut_error=False):
    import reader.__main__ as main_module

    events = []

    class FakeQApplication:
        @classmethod
        def instance(cls):
            return None

        def __init__(self, _argv):
            pass

        def exec(self):
            events.append("exec")
            return 17

    class FakeWindow:
        def open_paths(self, _paths):
            pass

        def show_status(self, message):
            events.append(("status", message))

    class FakeReaderApp:
        def __init__(self, _qapp):
            pass

        def is_primary_instance(self):
            return True

        def new_window(self):
            return FakeWindow()

    def register(*_args, **_kwargs):
        events.append("association")
        if association_error:
            raise OSError("registry denied")

    def shortcut(*_args, **_kwargs):
        events.append("shortcut")
        if shortcut_error:
            raise OSError("desktop denied")

    monkeypatch.setattr(main_module, "QApplication", FakeQApplication)
    monkeypatch.setattr(main_module, "ReaderApp", FakeReaderApp)
    monkeypatch.setattr(main_module, "append_smoke_batch", lambda _paths: None)
    monkeypatch.setattr(main_module, "_shell_integration_disabled", lambda: False)
    monkeypatch.setattr(main_module, "register_open_with", register)
    monkeypatch.setattr(main_module, "create_desktop_shortcut", shortcut)

    result = main_module.main(["Reader.exe"])
    return result, events


def test_association_failure_shows_hint_and_still_attempts_shortcut(monkeypatch):
    result, events = _run_primary_with_shell_failure(
        monkeypatch,
        association_error=True,
    )

    assert result == 17
    assert events[0:2] == ["association", ("status", "文件关联设置失败")]
    assert "shortcut" in events
    assert events[-1] == "exec"


def test_shortcut_failure_shows_hint_and_app_continues(monkeypatch):
    result, events = _run_primary_with_shell_failure(
        monkeypatch,
        shortcut_error=True,
    )

    assert result == 17
    assert "association" in events
    assert "shortcut" in events
    assert ("status", "桌面快捷方式创建失败") in events
    assert events[-1] == "exec"
