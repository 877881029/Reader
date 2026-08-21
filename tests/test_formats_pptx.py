from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from reader.formats.pptx import to_html


def test_pptx_emits_one_section_per_slide(tmp_path: Path):
    path = tmp_path / "s.pptx"
    prs = Presentation()
    layout = prs.slide_layouts[1]
    s1 = prs.slides.add_slide(layout)
    s1.shapes.title.text = "Slide One"
    s1.placeholders[1].text = "Alpha"
    s2 = prs.slides.add_slide(layout)
    s2.shapes.title.text = "Slide Two"
    s2.placeholders[1].text = "Beta"
    prs.save(path)
    result = to_html(path)
    assert result.html.count('class="slide"') == 2
    assert "Slide One" in result.html
    assert "Alpha" in result.html
    assert "Slide Two" in result.html
