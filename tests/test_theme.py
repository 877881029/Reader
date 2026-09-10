from pathlib import Path

from reader.theme import COBALT, PAPER, wrap_document_html

ROOT = Path(__file__).resolve().parents[1]


def test_wrap_document_html_uses_paper_and_cobalt() -> None:
    html = wrap_document_html("<p>hello</p>")
    compact = html.replace(" ", "").lower()
    assert PAPER.lower() in compact
    assert COBALT.lower() in compact
    assert "<p>hello</p>" in html


def test_md_viewer_source_uses_paper_tokens() -> None:
    css = (ROOT / "web" / "md-viewer" / "src" / "style.css").read_text(encoding="utf-8")
    assert f"--paper: {PAPER}" in css
    assert f"--accent: {COBALT}" in css


def test_pptx_viewer_source_uses_paper_shell_not_dark_slate() -> None:
    css = (ROOT / "web" / "pptx-viewer" / "src" / "style.css").read_text(encoding="utf-8")
    assert PAPER in css
    assert COBALT in css
    assert "#0f172a" not in css
    assert "background: white" in css


def _hashed_css(bundle: str) -> str:
    assets = ROOT / "assets" / bundle / "assets"
    css_files = sorted(assets.glob("*.css"))
    assert css_files, f"missing hashed css in {assets}"
    return css_files[0].read_text(encoding="utf-8")


def test_committed_viewer_bundles_use_paper_tokens() -> None:
    md_css = _hashed_css("md-viewer")
    pptx_css = _hashed_css("pptx-viewer")
    assert PAPER in md_css
    assert COBALT in md_css
    assert PAPER in pptx_css
    assert COBALT in pptx_css
    assert "#0f172a" not in pptx_css
