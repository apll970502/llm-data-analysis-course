from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"

FONT_PATH = Path(r"C:\Windows\Fonts\malgun.ttf")
if not FONT_PATH.exists():
    raise RuntimeError("맑은 고딕 폰트를 찾을 수 없습니다: " + str(FONT_PATH))

pdfmetrics.registerFont(TTFont("MalgunGothic", str(FONT_PATH)))

styles = getSampleStyleSheet()
for style_name in ["Title", "Heading1", "Heading2", "BodyText"]:
    styles[style_name].fontName = "MalgunGothic"

today = date.today().isoformat()
pdf_path = REPORTS_DIR / f"tourism_trend_report_{today}.pdf"

doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
story = []

story.append(Paragraph("관광 트렌드 자동 분석 보고서", styles["Title"]))
story.append(Spacer(1, 12))
story.append(Paragraph(f"분석 기준일: {today}", styles["BodyText"]))
story.append(Spacer(1, 16))

llm_path = REPORTS_DIR / "llm_summary.md"
if llm_path.exists():
    report_text = llm_path.read_text(encoding="utf-8")
    for line in report_text.splitlines():
        if line.strip():
            clean = escape(line.replace("**", "").lstrip("#").strip())
            story.append(Paragraph(clean, styles["BodyText"]))
            story.append(Spacer(1, 6))

for name in ["naver_trend.png", "tourism_consumption_top10.png"]:
    chart_path = REPORTS_DIR / name
    if chart_path.exists():
        story.append(Spacer(1, 12))
        story.append(Image(str(chart_path), width=450, height=250))

doc.build(story)

print("[PASS] PDF created:", pdf_path)
