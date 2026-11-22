"""Сборка паспорта проекта в .docx из Markdown без внешних зависимостей.

Формат: A4, поля 1,5 см, Times New Roman 9 pt, таблицы с сеткой.
Дополнительно оценивает число страниц по метрикам шрифта и ширины колонок.
"""

from __future__ import annotations

import pathlib
import re
import sys
import zipfile
from xml.sax.saxutils import escape

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT = pathlib.Path(__file__).resolve().parents[2]
SRC = PROJECT / "docs/passport/passport.md"
DST = PROJECT / "docs/passport/Паспорт_проекта_battalion_404.docx"

FONT = "Times New Roman"
SIZE_PT = 9.0
PAGE_W_CM, PAGE_H_CM = 21.0, 29.7
MARGIN_CM = 1.5
TEXT_W_PT = (PAGE_W_CM - 2 * MARGIN_CM) * 28.3465
TEXT_H_PT = (PAGE_H_CM - 2 * MARGIN_CM) * 28.3465
LINE_PT = SIZE_PT * 1.12
AVG_CHAR_PT = SIZE_PT * 0.46  # средняя ширина знака TNR для кириллицы+латиницы

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def twips(pt: float) -> int:
    return int(round(pt * 20))


def run_xml(text: str, bold: bool = False, size: float = SIZE_PT) -> str:
    props = f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'
    if bold:
        props += "<w:b/>"
    props += f'<w:sz w:val="{int(size * 2)}"/><w:szCs w:val="{int(size * 2)}"/>'
    return f"<w:r><w:rPr>{props}</w:rPr><w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"


def rich_runs(text: str, size: float = SIZE_PT) -> str:
    """Обрабатывает **жирный** и `код` внутри строки."""
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", text):
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            out.append(run_xml(part[2:-2], bold=True, size=size))
        elif part.startswith("`") and part.endswith("`"):
            out.append(run_xml(part[1:-1], size=size))
        else:
            out.append(run_xml(part, size=size))
    return "".join(out)


def para(text: str, *, size: float = SIZE_PT, bold: bool = False,
         before: float = 0, after: float = 2, keep_next: bool = False) -> str:
    ppr = f'<w:spacing w:before="{twips(before)}" w:after="{twips(after)}" w:line="{int(LINE_PT * 20)}" w:lineRule="exact"/>'
    if keep_next:
        ppr += "<w:keepNext/>"
    ppr += f'<w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}"/><w:sz w:val="{int(size * 2)}"/>{"<w:b/>" if bold else ""}</w:rPr>'
    body = run_xml(text, bold=bold, size=size) if bold else rich_runs(text, size=size)
    return f"<w:p><w:pPr>{ppr}</w:pPr>{body}</w:p>"


def table_xml(rows: list[list[str]]) -> str:
    ncol = len(rows[0])
    # Первая колонка уже: подписи полей/аспектов
    if ncol == 2:
        widths = [TEXT_W_PT * 0.24, TEXT_W_PT * 0.76]
    elif ncol == 3:
        widths = [TEXT_W_PT * 0.30, TEXT_W_PT * 0.36, TEXT_W_PT * 0.34]
    elif ncol == 4:
        widths = [TEXT_W_PT * 0.20, TEXT_W_PT * 0.13, TEXT_W_PT * 0.36, TEXT_W_PT * 0.31]
    elif ncol == 5:
        widths = [TEXT_W_PT * 0.15, TEXT_W_PT * 0.26, TEXT_W_PT * 0.26, TEXT_W_PT * 0.15, TEXT_W_PT * 0.18]
    else:
        widths = [TEXT_W_PT / ncol] * ncol
    grid = "".join(f'<w:gridCol w:w="{twips(w)}"/>' for w in widths)
    borders = (
        "<w:tblBorders>"
        + "".join(
            f'<w:{side} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
            for side in ("top", "left", "bottom", "right", "insideH", "insideV")
        )
        + "</w:tblBorders>"
    )
    tblpr = (
        f'<w:tblW w:w="{twips(TEXT_W_PT)}" w:type="dxa"/>'
        '<w:tblLayout w:type="fixed"/>'
        + borders
        + '<w:tblCellMar><w:top w:w="20" w:type="dxa"/><w:left w:w="60" w:type="dxa"/>'
        '<w:bottom w:w="20" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar>'
    )
    out = [f"<w:tbl><w:tblPr>{tblpr}</w:tblPr><w:tblGrid>{grid}</w:tblGrid>"]
    for ri, row in enumerate(rows):
        cells = []
        for ci, cell in enumerate(row):
            head = ri == 0
            shd = '<w:shd w:val="clear" w:color="auto" w:fill="EFEFEF"/>' if head else ""
            tcpr = f'<w:tcW w:w="{twips(widths[ci])}" w:type="dxa"/>{shd}<w:vAlign w:val="top"/>'
            p = para(cell, bold=head, after=0, before=0)
            cells.append(f"<w:tc><w:tcPr>{tcpr}</w:tcPr>{p}</w:tc>")
        trpr = "<w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>" if head else "<w:trPr><w:cantSplit/></w:trPr>"
        out.append(f"<w:tr>{trpr}{''.join(cells)}</w:tr>")
    out.append("</w:tbl>")
    # После таблицы нужен пустой абзац-разделитель
    out.append(para("", after=2))
    return "".join(out)


# --- разбор markdown ---------------------------------------------------------
lines = SRC.read_text(encoding="utf-8").splitlines()
body: list[str] = []
est_height = 0.0


def add_height(text_lines: int, size: float = SIZE_PT, extra: float = 2) -> None:
    global est_height
    est_height += text_lines * (size * 1.12) + extra


def wrapped_lines(text: str, width_pt: float, size: float = SIZE_PT) -> int:
    plain = text.replace("**", "").replace("`", "")
    capacity = max(8, int(width_pt / (size * AVG_CHAR_PT / SIZE_PT)))
    total = 0
    for segment in plain.split("\n"):
        total += max(1, -(-len(segment) // capacity))
    return total


i = 0
while i < len(lines):
    line = lines[i].rstrip()
    if not line.strip():
        i += 1
        continue
    if line.startswith("# "):
        body.append(para(line[2:], size=14, bold=True, after=4, keep_next=True))
        add_height(wrapped_lines(line[2:], TEXT_W_PT, 14), 14, 4)
        i += 1
        continue
    if line.startswith("## "):
        body.append(para(line[3:], size=10.5, bold=True, before=5, after=3, keep_next=True))
        add_height(wrapped_lines(line[3:], TEXT_W_PT, 10.5), 10.5, 8)
        i += 1
        continue
    if line.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            raw = lines[i].strip().strip("|")
            cells = [c.strip() for c in raw.split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                rows.append(cells)
            i += 1
        body.append(table_xml(rows))
        ncol = len(rows[0])
        if ncol == 2:
            frac = [0.24, 0.76]
        elif ncol == 3:
            frac = [0.30, 0.36, 0.34]
        elif ncol == 4:
            frac = [0.20, 0.13, 0.36, 0.31]
        elif ncol == 5:
            frac = [0.15, 0.26, 0.26, 0.15, 0.18]
        else:
            frac = [1 / ncol] * ncol
        for row in rows:
            h = max(wrapped_lines(c, TEXT_W_PT * frac[ci] - 6) for ci, c in enumerate(row))
            add_height(h, SIZE_PT, 3)
        add_height(1, SIZE_PT, 2)
        continue
    if re.match(r"^\d+\.\s", line):
        text = line
        body.append(para(text, after=1))
        add_height(wrapped_lines(text, TEXT_W_PT - 10), SIZE_PT, 1)
        i += 1
        continue
    body.append(para(line, after=3))
    add_height(wrapped_lines(line, TEXT_W_PT), SIZE_PT, 3)
    i += 1

sect = (
    f'<w:sectPr><w:pgSz w:w="{twips(PAGE_W_CM * 28.3465)}" w:h="{twips(PAGE_H_CM * 28.3465)}"/>'
    f'<w:pgMar w:top="{twips(MARGIN_CM * 28.3465)}" w:right="{twips(MARGIN_CM * 28.3465)}" '
    f'w:bottom="{twips(MARGIN_CM * 28.3465)}" w:left="{twips(MARGIN_CM * 28.3465)}" '
    f'w:header="0" w:footer="0" w:gutter="0"/>'
    '<w:cols w:space="708"/><w:docGrid w:linePitch="360"/></w:sectPr>'
)
document = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:document xmlns:w="{W[1:-1]}"><w:body>{"".join(body)}{sect}</w:body></w:document>'
)

styles = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    f'<w:styles xmlns:w="{W[1:-1]}">'
    "<w:docDefaults><w:rPrDefault><w:rPr>"
    f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:cs="{FONT}"/>'
    f'<w:sz w:val="{int(SIZE_PT * 2)}"/><w:szCs w:val="{int(SIZE_PT * 2)}"/>'
    '<w:lang w:val="ru-RU"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="40" w:line="200" w:lineRule="exact"/></w:pPr></w:pPrDefault>'
    "</w:docDefaults>"
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>'
    "</w:styles>"
)

content_types = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
    "</Types>"
)
rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)
doc_rels = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

DST.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("word/document.xml", document)
    z.writestr("word/styles.xml", styles)
    z.writestr("word/_rels/document.xml.rels", doc_rels)

print("создан:", DST, DST.stat().st_size, "байт")
print(f"оценка высоты содержимого: {est_height:.0f} pt")
print(f"высота полосы: {TEXT_H_PT:.0f} pt")
print(f"расчётное число страниц: {est_height / TEXT_H_PT:.2f}")