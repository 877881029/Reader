from __future__ import annotations


def test_webengine_warmup_is_idempotent(qapp):
    from reader.preview import webengine_warmup

    webengine_warmup.reset_warmup_for_tests()
    assert webengine_warmup.warmup_webengine(qapp) is True
    assert webengine_warmup.warmup_webengine(qapp) is False
