"""Build the HIS.Pro hospital operations manual DOCX from its Markdown source.

Design preset: compact_reference_guide.
Header pattern: customer_pack.
Named overrides: 30 pt cover title, 13.5 pt cover subtitle, and 9.5 pt
table text for dense operational matrices.
"""

from __future__ import annotations

import math
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


SOURCE = ROOT / "docs" / "13_HOSPITAL_OPERATIONS_MANUAL.md"
OUTPUT = ROOT / "docs" / "HIS_PRO_HOSPITAL_OPERATIONS_MANUAL.docx"

PAGE_WIDTH_DXA = 12240
PAGE_HEIGHT_DXA = 15840
CONTENT_WIDTH_DXA = 9360
TABLE_INDENT_DXA = 120
CELL_MARGIN_TOP_BOTTOM = 80
CELL_MARGIN_START_END = 120

BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
NAVY = "0B2545"
MUTED = "5B6573"
LIGHT_BLUE = "E8EEF5"
LIGHT_GRAY = "F4F6F9"
BORDER = "B8C2CC"
WHITE = "FFFFFF"
BLACK = "1D2733"


def set_run_font(
    run,
    *,
    name: str = "Calibri",
    size: float | None = None,
    color: str | None = None,
    bold: bool | None = None,
    italic: bool | None = None,
) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in (
        ("top", CELL_MARGIN_TOP_BOTTOM),
        ("bottom", CELL_MARGIN_TOP_BOTTOM),
        ("start", CELL_MARGIN_START_END),
        ("end", CELL_MARGIN_START_END),
    ):
        tag = qn(f"w:{edge}")
        element = tc_mar.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            tc_mar.append(element)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.find(qn("w:tblBorders"))
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = borders.find(qn(f"w:{edge}"))
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), BORDER)


def table_widths(rows: list[list[str]]) -> list[int]:
    columns = max(len(row) for row in rows)
    lengths = []
    for index in range(columns):
        maximum = max(
            len(row[index]) if index < len(row) else 0
            for row in rows
        )
        lengths.append(max(5.0, math.sqrt(min(maximum, 180))))

    minimum = 1000 if columns >= 4 else 1200
    if minimum * columns >= CONTENT_WIDTH_DXA:
        minimum = CONTENT_WIDTH_DXA // columns
    distributable = CONTENT_WIDTH_DXA - (minimum * columns)
    total_weight = sum(lengths)
    widths = [minimum + round(distributable * weight / total_weight) for weight in lengths]
    widths[-1] += CONTENT_WIDTH_DXA - sum(widths)
    return widths


def apply_table_geometry(table, widths: list[int]) -> None:
    table.autofit = False
    tbl_pr = table._tbl.tblPr

    tbl_w = tbl_pr.find(qn("w:tblW"))
    if tbl_w is None:
        tbl_w = OxmlElement("w:tblW")
        tbl_pr.insert(0, tbl_w)
    tbl_w.set(qn("w:w"), str(CONTENT_WIDTH_DXA))
    tbl_w.set(qn("w:type"), "dxa")

    tbl_ind = tbl_pr.find(qn("w:tblInd"))
    if tbl_ind is None:
        tbl_ind = OxmlElement("w:tblInd")
        tbl_pr.append(tbl_ind)
    tbl_ind.set(qn("w:w"), str(TABLE_INDENT_DXA))
    tbl_ind.set(qn("w:type"), "dxa")

    layout = tbl_pr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tbl_pr.append(layout)
    layout.set(qn("w:type"), "fixed")

    grid = table._tbl.tblGrid
    for child in list(grid):
        grid.remove(child)
    for width in widths:
        grid_col = OxmlElement("w:gridCol")
        grid_col.set(qn("w:w"), str(width))
        grid.append(grid_col)

    for row in table.rows:
        for index, cell in enumerate(row.cells):
            width = widths[min(index, len(widths) - 1)]
            tc_pr = cell._tc.get_or_add_tcPr()
            tc_w = tc_pr.find(qn("w:tcW"))
            if tc_w is None:
                tc_w = OxmlElement("w:tcW")
                tc_pr.append(tc_w)
            tc_w.set(qn("w:w"), str(width))
            tc_w.set(qn("w:type"), "dxa")
            set_cell_margins(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

    set_table_borders(table)


def add_table(doc: Document, rows: list[list[str]], *, header: bool = True):
    columns = max(len(row) for row in rows)
    normalized = [row + [""] * (columns - len(row)) for row in rows]
    table = doc.add_table(rows=len(normalized), cols=columns)
    widths = table_widths(normalized)
    apply_table_geometry(table, widths)

    for row_index, values in enumerate(normalized):
        row = table.rows[row_index]
        if row_index == 0 and header:
            set_repeat_table_header(row)
        for column_index, value in enumerate(values):
            cell = row.cells[column_index]
            cell.text = ""
            if row_index == 0 and header:
                set_cell_shading(cell, LIGHT_BLUE)
            paragraph = cell.paragraphs[0]
            paragraph.style = doc.styles["Table Text"]
            paragraph.paragraph_format.space_after = Pt(0)
            add_inline_runs(
                paragraph,
                value,
                default_size=9.5,
                force_bold=(row_index == 0 and header),
            )
    doc.add_paragraph(style="Table Spacer")
    return table


def add_field(paragraph, instruction: str) -> None:
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run = paragraph.add_run()
    run._r.extend([begin, instr, separate, text, end])
    set_run_font(run, size=8.5, color=MUTED)


def configure_header_footer(section) -> None:
    section.different_first_page_header_footer = True

    first_header = section.first_page_header
    paragraph = first_header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run("HIS.PRO  |  HOSPITAL OPERATIONS")
    set_run_font(run, size=8.5, color=MUTED, bold=True)

    header = section.header
    paragraph = header.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    tabs = paragraph.paragraph_format.tab_stops
    tabs.add_tab_stop(Inches(6.5))
    left = paragraph.add_run("HIS.Pro Hospital Operations Manual")
    set_run_font(left, size=8.5, color=MUTED, bold=True)
    right = paragraph.add_run("\tConfidential")
    set_run_font(right, size=8.5, color=MUTED)

    for footer in (section.first_page_footer, section.footer):
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        label = paragraph.add_run("HIS.Pro  |  Page ")
        set_run_font(label, size=8.5, color=MUTED)
        add_field(paragraph, "PAGE")
        of_run = paragraph.add_run(" of ")
        set_run_font(of_run, size=8.5, color=MUTED)
        add_field(paragraph, "NUMPAGES")


def configure_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(BLACK)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    heading_tokens = {
        "Heading 1": (16, BLUE, 18, 10),
        "Heading 2": (13, BLUE, 14, 7),
        "Heading 3": (12, DARK_BLUE, 10, 5),
    }
    for name, (size, color, before, after) in heading_tokens.items():
        style = styles[name]
        style.font.name = "Calibri"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = 1.0
        style.paragraph_format.keep_with_next = True

    custom_styles = {
        "Cover Kicker": (9, BLUE, True, False, 0, 3, 1.0),
        "Cover Title": (30, NAVY, True, False, 0, 8, 1.0),
        "Cover Subtitle": (13.5, MUTED, False, False, 0, 18, 1.15),
        "Lead Callout": (10.5, NAVY, True, False, 8, 8, 1.2),
        "Table Text": (9.5, BLACK, False, False, 0, 0, 1.15),
        "Table Spacer": (2, BLACK, False, False, 0, 5, 1.0),
        "Code Block": (9.5, NAVY, False, False, 3, 6, 1.05),
        "TOC Entry": (10.5, BLACK, False, False, 0, 3, 1.15),
    }
    for name, (size, color, bold, italic, before, after, spacing) in custom_styles.items():
        if name in styles:
            style = styles[name]
        else:
            style = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.font.name = "Calibri" if name != "Code Block" else "Consolas"
        style._element.rPr.rFonts.set(qn("w:ascii"), style.font.name)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), style.font.name)
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = bold
        style.font.italic = italic
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.line_spacing = spacing


def next_numbering_id(numbering, attribute: str) -> int:
    values = []
    for element in numbering:
        value = element.get(qn(attribute))
        if value is not None and str(value).isdigit():
            values.append(int(value))
    return max(values, default=0) + 1


def create_abstract_numbering(
    doc: Document, *, bullet: bool, bullet_character: str = "\u2022"
) -> int:
    numbering = doc.part.numbering_part.element
    abstract_id = next_numbering_id(numbering, "w:abstractNumId")
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))

    multi = OxmlElement("w:multiLevelType")
    multi.set(qn("w:val"), "singleLevel")
    abstract.append(multi)

    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    level.append(start)
    num_fmt = OxmlElement("w:numFmt")
    num_fmt.set(qn("w:val"), "bullet" if bullet else "decimal")
    level.append(num_fmt)
    level_text = OxmlElement("w:lvlText")
    level_text.set(qn("w:val"), bullet_character if bullet else "%1.")
    level.append(level_text)
    level_jc = OxmlElement("w:lvlJc")
    level_jc.set(qn("w:val"), "left")
    level.append(level_jc)

    p_pr = OxmlElement("w:pPr")
    tabs = OxmlElement("w:tabs")
    tab = OxmlElement("w:tab")
    tab.set(qn("w:val"), "num")
    tab.set(qn("w:pos"), "540")
    tabs.append(tab)
    p_pr.append(tabs)
    indent = OxmlElement("w:ind")
    indent.set(qn("w:left"), "540")
    indent.set(qn("w:hanging"), "271")
    p_pr.append(indent)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:after"), "80")
    spacing.set(qn("w:line"), "300")
    spacing.set(qn("w:lineRule"), "auto")
    p_pr.append(spacing)
    level.append(p_pr)

    r_pr = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "Calibri")
    fonts.set(qn("w:hAnsi"), "Calibri")
    r_pr.append(fonts)
    level.append(r_pr)

    abstract.append(level)
    numbering.append(abstract)
    return abstract_id


def create_num_instance(doc: Document, abstract_id: int, *, restart: bool = False) -> int:
    numbering = doc.part.numbering_part.element
    num_id = next_numbering_id(numbering, "w:numId")
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract = OxmlElement("w:abstractNumId")
    abstract.set(qn("w:val"), str(abstract_id))
    num.append(abstract)
    if restart:
        override = OxmlElement("w:lvlOverride")
        override.set(qn("w:ilvl"), "0")
        start = OxmlElement("w:startOverride")
        start.set(qn("w:val"), "1")
        override.append(start)
        num.append(override)
    numbering.append(num)
    return num_id


def set_list_numbering(paragraph, num_id: int) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    num_pr = p_pr.find(qn("w:numPr"))
    if num_pr is None:
        num_pr = OxmlElement("w:numPr")
        p_pr.append(num_pr)
    ilvl = OxmlElement("w:ilvl")
    ilvl.set(qn("w:val"), "0")
    number = OxmlElement("w:numId")
    number.set(qn("w:val"), str(num_id))
    num_pr.extend([ilvl, number])
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.line_spacing = 1.25


INLINE_PATTERN = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)")


def clean_links(value: str) -> str:
    return re.sub(r"\[([^]]+)]\(([^)]+)\)", r"\1 (\2)", value)


def add_inline_runs(
    paragraph,
    text: str,
    *,
    default_size: float | None = None,
    force_bold: bool = False,
) -> None:
    text = clean_links(text)
    cursor = 0
    for match in INLINE_PATTERN.finditer(text):
        if match.start() > cursor:
            run = paragraph.add_run(text[cursor:match.start()])
            set_run_font(run, size=default_size, bold=force_bold)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, size=default_size, bold=True)
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, name="Consolas", size=default_size or 10, color=NAVY, bold=force_bold)
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, size=default_size, italic=True, bold=force_bold)
        cursor = match.end()
    if cursor < len(text):
        run = paragraph.add_run(text[cursor:])
        set_run_font(run, size=default_size, bold=force_bold)


def shade_paragraph(paragraph, fill: str, border_color: str = BLUE) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    p_pr.append(shading)
    borders = OxmlElement("w:pBdr")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), "18")
    left.set(qn("w:space"), "8")
    left.set(qn("w:color"), border_color)
    borders.append(left)
    p_pr.append(borders)


def add_cover(doc: Document) -> None:
    paragraph = doc.add_paragraph(style="Cover Kicker")
    paragraph.add_run("CUSTOMER OPERATIONS PACK")

    paragraph = doc.add_paragraph(style="Cover Title")
    paragraph.add_run("HIS.Pro Hospital Operations Manual")

    paragraph = doc.add_paragraph(style="Cover Subtitle")
    paragraph.add_run(
        "Deployment, administration, daily use, security, data migration, downtime, and go-live guidance"
    )

    add_table(
        doc,
        [
            ["Document detail", "Value"],
            ["Prepared for", "HIS.Pro hospital customers"],
            ["Release", "1.0 release-candidate draft"],
            ["Baseline", "31 July 2026"],
            ["Classification", "Confidential - hospital operational documentation"],
        ],
        header=True,
    )

    paragraph = doc.add_paragraph(style="Lead Callout")
    paragraph.add_run(
        "Approval status: Draft for hospital review. General availability remains NO-GO until the launch-readiness evidence is signed."
    )
    shade_paragraph(paragraph, LIGHT_GRAY)

    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(22)
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run("HIS.PRO")
    set_run_font(run, size=11, color=BLUE, bold=True)

    doc.add_page_break()


def add_contents(doc: Document, headings: list[str]) -> None:
    heading = doc.add_paragraph("Contents", style="Heading 1")
    heading.paragraph_format.space_before = Pt(0)
    for item in headings:
        paragraph = doc.add_paragraph(style="TOC Entry")
        paragraph.paragraph_format.left_indent = Inches(0.18)
        paragraph.paragraph_format.first_line_indent = Inches(-0.18)
        run = paragraph.add_run(item)
        set_run_font(run, size=10.5, color=NAVY)
    doc.add_page_break()


def parse_table(lines: list[str], start: int) -> tuple[list[list[str]], int]:
    rows: list[list[str]] = []
    index = start
    while index < len(lines) and lines[index].strip().startswith("|"):
        values = [value.strip() for value in lines[index].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{3,}:?", value or "") for value in values):
            rows.append(values)
        index += 1
    return rows, index


def build_document() -> Document:
    source_lines = SOURCE.read_text(encoding="utf-8").splitlines()
    major_headings = [
        line.removeprefix("## ").strip()
        for line in source_lines
        if line.startswith("## ")
    ]

    doc = Document()
    section = doc.sections[0]
    section.start_type = WD_SECTION_START.NEW_PAGE
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.right_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)
    configure_header_footer(section)
    configure_styles(doc)

    doc.core_properties.title = "HIS.Pro Hospital Operations Manual"
    doc.core_properties.subject = "Hospital deployment, administration, daily use, security, and go-live"
    doc.core_properties.author = "HIS.Pro"
    doc.core_properties.keywords = "HIS.Pro, hospital information system, operations, security, billing, migration"

    bullet_abstract = create_abstract_numbering(doc, bullet=True)
    checkbox_abstract = create_abstract_numbering(
        doc, bullet=True, bullet_character="[ ]"
    )
    decimal_abstract = create_abstract_numbering(doc, bullet=False)
    bullet_num = create_num_instance(doc, bullet_abstract)
    checkbox_num = create_num_instance(doc, checkbox_abstract)
    active_decimal_num: int | None = None
    previous_was_decimal = False

    add_cover(doc)
    add_contents(doc, major_headings)

    # The cover consumes the source title, subtitle, and opening metadata table.
    start_index = next(
        index for index, line in enumerate(source_lines) if line == "## Document Control"
    )
    lines = source_lines[start_index:]
    index = 0
    in_code = False
    code_lines: list[str] = []

    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()

        if stripped.startswith("```"):
            if in_code:
                paragraph = doc.add_paragraph(style="Code Block")
                shade_paragraph(paragraph, LIGHT_GRAY, border_color=DARK_BLUE)
                for line_index, code_line in enumerate(code_lines):
                    if line_index:
                        paragraph.add_run().add_break()
                    run = paragraph.add_run(code_line)
                    set_run_font(run, name="Consolas", size=9.5, color=NAVY)
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(raw)
            index += 1
            continue

        if not stripped:
            previous_was_decimal = False
            index += 1
            continue

        if stripped.startswith("|"):
            rows, index = parse_table(lines, index)
            if rows:
                add_table(doc, rows, header=len(rows) > 1)
            previous_was_decimal = False
            continue

        heading_match = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if heading_match:
            level = len(heading_match.group(1)) - 1
            title = heading_match.group(2).strip()
            paragraph = doc.add_paragraph(style=f"Heading {level}")
            if level == 1 and re.match(r"^\d+\.", title):
                paragraph.paragraph_format.page_break_before = True
            add_inline_runs(paragraph, title)
            previous_was_decimal = False
            index += 1
            continue

        bullet_match = re.match(r"^-\s+(.+)$", stripped)
        if bullet_match:
            item = bullet_match.group(1)
            paragraph = doc.add_paragraph()
            if item.startswith("[ ] "):
                set_list_numbering(paragraph, checkbox_num)
                item = item[4:]
            else:
                set_list_numbering(paragraph, bullet_num)
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
            add_inline_runs(paragraph, item)
            previous_was_decimal = False
            index = continuation
            continue

        decimal_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if decimal_match:
            if not previous_was_decimal:
                active_decimal_num = create_num_instance(doc, decimal_abstract, restart=True)
            paragraph = doc.add_paragraph()
            set_list_numbering(paragraph, active_decimal_num)
            item = decimal_match.group(1)
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
            add_inline_runs(paragraph, item)
            previous_was_decimal = True
            index = continuation
            continue

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
        paragraph = doc.add_paragraph()
        add_inline_runs(paragraph, " ".join(paragraph_lines))
        previous_was_decimal = False
        index = lookahead

    return doc


def main() -> None:
    document = build_document()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    print(f"Built {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
