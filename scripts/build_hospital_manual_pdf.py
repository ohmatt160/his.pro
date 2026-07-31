"""Build the visually verified HIS.Pro hospital operations PDF."""

from __future__ import annotations

import math
import re
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "13_HOSPITAL_OPERATIONS_MANUAL.md"
OUTPUT = ROOT / "output" / "pdf" / "HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.pdf"

BLUE = colors.HexColor("#2E74B5")
DARK_BLUE = colors.HexColor("#1F4D78")
NAVY = colors.HexColor("#0B2545")
MUTED = colors.HexColor("#5B6573")
LIGHT_BLUE = colors.HexColor("#E8EEF5")
LIGHT_GRAY = colors.HexColor("#F4F6F9")
BORDER = colors.HexColor("#B8C2CC")
INK = colors.HexColor("#1D2733")
CONTENT_WIDTH = 6.5 * inch


def register_fonts() -> None:
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("Calibri", font_dir / "calibri.ttf"))
    pdfmetrics.registerFont(TTFont("Calibri-Bold", font_dir / "calibrib.ttf"))
    pdfmetrics.registerFont(TTFont("Calibri-Italic", font_dir / "calibrii.ttf"))
    pdfmetrics.registerFontFamily(
        "Calibri",
        normal="Calibri",
        bold="Calibri-Bold",
        italic="Calibri-Italic",
        boldItalic="Calibri-Bold",
    )


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_furniture(page_count)
            super().showPage()
        super().save()

    def draw_furniture(self, page_count: int) -> None:
        width, height = letter
        self.saveState()
        self.setFillColor(MUTED)
        self.setFont("Calibri-Bold", 8.5)
        if self._pageNumber == 1:
            self.drawString(inch, height - 0.58 * inch, "HIS.PRO  |  HOSPITAL OPERATIONS")
        else:
            self.drawString(inch, height - 0.58 * inch, "HIS.Pro Hospital Operations Manual")
            self.setFont("Calibri", 8.5)
            self.drawRightString(width - inch, height - 0.58 * inch, "Confidential")
        self.setFont("Calibri", 8.5)
        self.drawRightString(
            width - inch,
            0.55 * inch,
            f"HIS.Pro  |  Page {self._pageNumber} of {page_count}",
        )
        self.restoreState()


def styles() -> dict[str, ParagraphStyle]:
    sample = getSampleStyleSheet()
    body = ParagraphStyle(
        "Body",
        parent=sample["BodyText"],
        fontName="Calibri",
        fontSize=11,
        leading=13.75,
        textColor=INK,
        spaceBefore=0,
        spaceAfter=6,
        allowWidows=0,
        allowOrphans=0,
    )
    return {
        "body": body,
        "h1": ParagraphStyle(
            "Heading1",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=16,
            leading=18,
            textColor=BLUE,
            spaceBefore=18,
            spaceAfter=10,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=13,
            leading=15,
            textColor=BLUE,
            spaceBefore=14,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h3": ParagraphStyle(
            "Heading3",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=12,
            leading=14,
            textColor=DARK_BLUE,
            spaceBefore=10,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "kicker": ParagraphStyle(
            "CoverKicker",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=9,
            leading=11,
            textColor=BLUE,
            spaceAfter=3,
        ),
        "title": ParagraphStyle(
            "CoverTitle",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=30,
            leading=32,
            textColor=NAVY,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=body,
            fontName="Calibri",
            fontSize=13.5,
            leading=16,
            textColor=MUTED,
            spaceAfter=18,
        ),
        "table": ParagraphStyle(
            "TableText",
            parent=body,
            fontName="Calibri",
            fontSize=9.5,
            leading=11,
            spaceAfter=0,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=9.5,
            leading=11,
            textColor=NAVY,
            spaceAfter=0,
        ),
        "toc": ParagraphStyle(
            "TOCEntry",
            parent=body,
            fontName="Calibri",
            fontSize=10.5,
            leading=12,
            textColor=NAVY,
            leftIndent=13,
            firstLineIndent=-13,
            spaceAfter=3,
        ),
        "code": ParagraphStyle(
            "CodeBlock",
            parent=body,
            fontName="Courier",
            fontSize=9.5,
            leading=10.5,
            textColor=NAVY,
            leftIndent=8,
            rightIndent=8,
            spaceBefore=3,
            spaceAfter=6,
            backColor=LIGHT_GRAY,
            borderColor=DARK_BLUE,
            borderWidth=0.7,
            borderPadding=7,
        ),
        "callout": ParagraphStyle(
            "Callout",
            parent=body,
            fontName="Calibri-Bold",
            fontSize=10.5,
            leading=12.5,
            textColor=NAVY,
            leftIndent=10,
            rightIndent=8,
            spaceBefore=8,
            spaceAfter=8,
            backColor=LIGHT_GRAY,
            borderColor=BLUE,
            borderWidth=1,
            borderPadding=8,
        ),
    }


INLINE_PATTERN = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def inline_markup(value: str) -> str:
    value = re.sub(r"\[([^]]+)]\(([^)]+)\)", r"\1 (\2)", value)
    output = []
    cursor = 0
    for match in INLINE_PATTERN.finditer(value):
        output.append(escape(value[cursor:match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            output.append(f"<b>{escape(token[2:-2])}</b>")
        elif token.startswith("`"):
            output.append(f'<font name="Courier">{escape(token[1:-1])}</font>')
        else:
            output.append(f"<i>{escape(token[1:-1])}</i>")
        cursor = match.end()
    output.append(escape(value[cursor:]))
    return "".join(output)


def table_widths(rows: list[list[str]]) -> list[float]:
    columns = max(len(row) for row in rows)
    weights = []
    for index in range(columns):
        maximum = max(len(row[index]) if index < len(row) else 0 for row in rows)
        weights.append(max(5.0, math.sqrt(min(maximum, 180))))
    minimum = 50 if columns >= 4 else 60
    available = CONTENT_WIDTH - minimum * columns
    widths = [minimum + available * weight / sum(weights) for weight in weights]
    widths[-1] += CONTENT_WIDTH - sum(widths)
    return widths


def make_table(rows: list[list[str]], style_map, *, header: bool = True) -> Table:
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    data = []
    for row_index, row in enumerate(normalized):
        paragraph_style = style_map["table_header"] if row_index == 0 and header else style_map["table"]
        data.append([Paragraph(inline_markup(value), paragraph_style) for value in row])
    table = Table(
        data,
        colWidths=table_widths(normalized),
        repeatRows=1 if header else 0,
        hAlign="LEFT",
    )
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        values = [value.strip() for value in lines[index].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", value or "") for value in values):
            rows.append(values)
        index += 1
    return rows, index


def build_story(style_map):
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    headings = [line.removeprefix("## ").strip() for line in lines if line.startswith("## ")]
    story = [
        Spacer(1, 0.35 * inch),
        Paragraph("CUSTOMER OPERATIONS PACK", style_map["kicker"]),
        Paragraph("HIS.Pro Hospital Operations Manual", style_map["title"]),
        Paragraph(
            "Deployment, administration, daily use, security, data migration, downtime, and go-live guidance",
            style_map["subtitle"],
        ),
        make_table(
            [
                ["Document detail", "Value"],
                ["Prepared for", "HIS.Pro hospital customers"],
                ["Release", "1.0 release-candidate draft"],
                ["Baseline", "31 July 2026"],
                ["Classification", "Confidential - hospital operational documentation"],
            ],
            style_map,
            header=True,
        ),
        Spacer(1, 12),
        Paragraph(
            "Approval status: Draft for hospital review. General availability remains NO-GO until the launch-readiness evidence is signed.",
            style_map["callout"],
        ),
        Spacer(1, 34),
        Paragraph("<b>HIS.PRO</b>", style_map["body"]),
        PageBreak(),
        Paragraph("Contents", style_map["h1"]),
    ]
    story.extend(Paragraph(inline_markup(item), style_map["toc"]) for item in headings)
    story.append(PageBreak())

    start_index = next(index for index, line in enumerate(lines) if line == "## Document Control")
    lines = lines[start_index:]
    index = 0
    list_kind = None
    list_items = []

    def flush_list():
        nonlocal list_kind, list_items
        if not list_items:
            return
        flow_items = [
            ListItem(
                Paragraph(inline_markup(item), style_map["body"]),
                leftIndent=0,
                spaceAfter=4,
            )
            for item in list_items
        ]
        list_options = {
            "bulletType": "1" if list_kind == "decimal" else "bullet",
            "bulletFontName": "Calibri",
            "bulletFontSize": 11,
            "leftIndent": 27,
            "bulletOffsetY": 1,
            "spaceAfter": 2,
        }
        if list_kind == "decimal":
            list_options["start"] = 1
        elif list_kind == "check":
            list_options["start"] = "[ ]"
        story.append(ListFlowable(flow_items, **list_options))
        list_kind = None
        list_items = []

    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            flush_list()
            index += 1
            continue

        if stripped.startswith("```"):
            flush_list()
            code_lines = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            story.append(Preformatted("\n".join(code_lines), style_map["code"] or style_map["body"]))
            continue

        if stripped.startswith("|"):
            flush_list()
            rows, index = parse_table(lines, index)
            if rows:
                story.extend([make_table(rows, style_map, header=len(rows) > 1), Spacer(1, 5)])
            continue

        heading_match = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1)) - 1
            title = heading_match.group(2).strip()
            if level == 1 and (title == "Document Control" or re.match(r"^\d+\.", title)):
                if story and not isinstance(story[-1], PageBreak):
                    story.append(PageBreak())
            story.append(Paragraph(inline_markup(title), style_map[f"h{level}"]))
            index += 1
            continue

        bullet = re.match(r"^-\s+(.+)$", stripped)
        decimal = re.match(r"^\d+\.\s+(.+)$", stripped)
        if bullet or decimal:
            item = (bullet or decimal).group(1)
            kind = "bullet" if bullet else "decimal"
            if bullet and item.startswith("[ ] "):
                kind = "check"
                item = item[4:]
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            continuation = index + 1
            while continuation < len(lines):
                candidate_raw = lines[continuation]
                candidate = candidate_raw.strip()
                if not candidate or not candidate_raw[:1].isspace():
                    break
                if (
                    candidate.startswith("#")
                    or candidate.startswith("|")
                    or candidate.startswith("```")
                    or re.match(r"^-\s+", candidate)
                    or re.match(r"^\d+\.\s+", candidate)
                ):
                    break
                item += " " + candidate
                continuation += 1
            list_items.append(item)
            index = continuation
            continue

        flush_list()
        paragraph_lines = [stripped]
        lookahead = index + 1
        while lookahead < len(lines):
            candidate = lines[lookahead].strip()
            if (
                not candidate
                or candidate.startswith("#")
                or candidate.startswith("|")
                or candidate.startswith("```")
                or re.match(r"^-\s+", candidate)
                or re.match(r"^\d+\.\s+", candidate)
            ):
                break
            paragraph_lines.append(candidate)
            lookahead += 1
        story.append(Paragraph(inline_markup(" ".join(paragraph_lines)), style_map["body"]))
        index = lookahead

    flush_list()
    return story


def main() -> None:
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    style_map = styles()
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
        title="HIS.Pro Hospital Operations Manual",
        author="HIS.Pro",
        subject="Hospital deployment, administration, daily use, security, and go-live",
    )
    document.build(build_story(style_map), canvasmaker=NumberedCanvas)
    print(f"Built {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
