import pytest

from reader.ext import convert, dual_pane, translate


def test_stubs_disabled():
    assert dual_pane.ENABLED is False
    assert convert.ENABLED is False
    assert translate.ENABLED is False
    with pytest.raises(NotImplementedError):
        dual_pane.split_view()
    with pytest.raises(NotImplementedError):
        convert.convert_file()
    with pytest.raises(NotImplementedError):
        translate.translate_document()
