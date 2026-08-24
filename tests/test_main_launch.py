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
