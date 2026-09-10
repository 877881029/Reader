from __future__ import annotations

import pytest

from reader.shell.settings_claim import SETTINGS_URI, claim_protected_defaults


def test_claim_protected_defaults_skips_settings_when_pdf_already_reader() -> None:
    events: list[object] = []

    claim_protected_defaults(
        query_app=lambda _ext: "Reader",
        open_settings=lambda uri: events.append(("open", uri)),
        invoke_file_types=lambda exts: events.append(("invoke", tuple(exts))),
        close_settings=lambda: events.append("close"),
        sleep=lambda _seconds: None,
        timeout_s=0,
    )

    assert events == []


def test_claim_protected_defaults_opens_reader_page_and_invokes_pdf() -> None:
    state = {".pdf": "Adobe Acrobat"}
    events: list[object] = []

    def query(ext: str) -> str:
        return state.get(ext, "Reader")

    def invoke(exts: list[str]) -> None:
        events.append(("invoke", tuple(exts)))
        for ext in exts:
            state[ext] = "Reader"

    claim_protected_defaults(
        query_app=query,
        open_settings=lambda uri: events.append(("open", uri)),
        invoke_file_types=invoke,
        close_settings=lambda: events.append("close"),
        sleep=lambda _seconds: None,
        timeout_s=12,
    )

    assert events[0] == ("open", SETTINGS_URI)
    assert ("invoke", (".pdf",)) in events
    assert events[-1] == "close"


def test_claim_protected_defaults_closes_settings_when_invoke_fails() -> None:
    events: list[object] = []

    def invoke(_exts: list[str]) -> None:
        events.append("invoke")
        raise RuntimeError("ui failed")

    with pytest.raises(RuntimeError, match="ui failed"):
        claim_protected_defaults(
            query_app=lambda _ext: "Adobe Acrobat",
            open_settings=lambda uri: events.append(("open", uri)),
            invoke_file_types=invoke,
            close_settings=lambda: events.append("close"),
            sleep=lambda _seconds: None,
            timeout_s=0,
        )

    assert events[0] == ("open", SETTINGS_URI)
    assert "invoke" in events
    assert events[-1] == "close"
