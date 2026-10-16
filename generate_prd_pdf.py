from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Preformatted,
    PageBreak,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "TalentNet_PRD_MVP_Demo.md"
OUTPUT = ROOT / "TalentNet_PRD_MVP_Demo.pdf"
FONT_REGULAR = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"
FONT_FALLBACK = r"C:\Windows\Fonts\msyh.ttc"


def register_fonts():
    font_path = FONT_REGULAR if Path(FONT_REGULAR).exists() else FONT_FALLBACK
    pdfmetrics.registerFont(TTFont("CN", font_path))
    pdfmetrics.registerFont(TTFont("CN-Bold", font_path))


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def inline(text: str) -> str:
    text = esc(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    return text


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="CN-Bold",
            fontSize=22,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#172033"),
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontName="CN-Bold",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#163B57"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontName="CN-Bold",
            fontSize=13,
            leading=19,
            textColor=colors.HexColor("#24556E"),
            spaceBefore=10,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontName="CN",
            fontSize=9.5,
            leading=15,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#222222"),
            spaceAfter=5,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["BodyText"],
            fontName="CN",
            fontSize=9.5,
            leading=15,
            leftIndent=13,
            firstLineIndent=-8,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#1F2933"),
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["BodyText"],
            fontName="CN",
            fontSize=8.2,
            leading=11,
            textColor=colors.HexColor("#202124"),
        ),
        "cell_header": ParagraphStyle(
            "cell_header",
            parent=base["BodyText"],
            fontName="CN-Bold",
            fontSize=8.3,
            leading=11,
            textColor=colors.white,
        ),
    }


def page(canvas, doc):
    canvas.saveState()
    canvas.setFont("CN", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(18 * mm, 10 * mm, "TalentNet MVP Demo PRD V3.0")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def parse_table(lines, styles):
    rows = []
    for line in lines:
        if re.match(r"^\|\s*-", line):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        rows.append(parts)
    if not rows:
        return None
    max_cols = max(len(r) for r in rows)
    normalized = []
    for i, row in enumerate(rows):
        row = row + [""] * (max_cols - len(row))
        style = styles["cell_header"] if i == 0 else styles["cell"]
        normalized.append([Paragraph(inline(cell), style) for cell in row])
    width = 174 * mm
    col_widths = [width / max_cols] * max_cols
    table = Table(normalized, colWidths=col_widths, hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24556E")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D5DEE4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ]
        )
    )
    return table


def build_story(md: str, styles):
    story = []
    lines = md.splitlines()
    i = 0
    in_code = False
    code_lines = []
    table_lines = []

    def flush_table():
        nonlocal table_lines
        if table_lines:
            table = parse_table(table_lines, styles)
            if table:
                story.append(table)
                story.append(Spacer(1, 6))
            table_lines = []

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_table()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["code"]))
                story.append(Spacer(1, 6))
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if line.startswith("|"):
            table_lines.append(line)
            i += 1
            continue
        flush_table()
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
        elif stripped.startswith("# "):
            story.append(Paragraph(inline(stripped[2:]), styles["title"]))
            story.append(Spacer(1, 10))
        elif stripped.startswith("## "):
            story.append(Paragraph(inline(stripped[3:]), styles["h1"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(inline(stripped[4:]), styles["h2"]))
        elif re.match(r"^\d+\.\s+", stripped):
            story.append(Paragraph(inline(stripped), styles["bullet"]))
        elif stripped.startswith("- "):
            story.append(Paragraph("• " + inline(stripped[2:]), styles["bullet"]))
        else:
            story.append(Paragraph(inline(stripped), styles["body"]))
        i += 1
    flush_table()
    return story


def main():
    register_fonts()
    styles = make_styles()
    md = SOURCE.read_text(encoding="utf-8")
    story = build_story(md, styles)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="TalentNet MVP Demo PRD V3.0",
        author="Codex",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="prd", frames=[frame], onPage=page)])
    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    main()
