import sys


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
