from io import BytesIO
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.chart.data import ChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches


out = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "pptx"
    / "visual-elements.pptx"
)

presentation = Presentation()

slide = presentation.slides.add_slide(presentation.slide_layouts[1])
slide.background.fill.solid()
slide.background.fill.fore_color.rgb = RGBColor(20, 48, 90)
slide.shapes.title.text = "Inherited title"
image = BytesIO()
Image.new("RGB", (320, 180), (37, 99, 235)).save(image, "PNG")
image.seek(0)
slide.shapes.add_picture(image, Inches(7), Inches(2), width=Inches(4))

slide = presentation.slides.add_slide(presentation.slide_layouts[6])
table = slide.shapes.add_table(
    3, 3, Inches(1), Inches(1), Inches(10), Inches(3)
).table
for row_index, row in enumerate(
    (("Metric", "Q1", "Q2"), ("A", "10", "14"), ("B", "8", "13"))
):
    for column_index, value in enumerate(row):
        table.cell(row_index, column_index).text = value

slide = presentation.slides.add_slide(presentation.slide_layouts[6])
chart_data = ChartData()
chart_data.categories = ["North", "South", "West"]
chart_data.add_series("Revenue", (12, 18, 15))
slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(1),
    Inches(1),
    Inches(10),
    Inches(5),
    chart_data,
)

slide = presentation.slides.add_slide(presentation.slide_layouts[6])
box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
box.text = "Missing font continues"
box.text_frame.paragraphs[0].runs[0].font.name = "ReaderMissingFontZZ"

out.parent.mkdir(parents=True, exist_ok=True)
presentation.save(out)
