"""Genera el PDF del manual de uso de NemoOC Web desde el markdown fuente."""

from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
    XPreformatted,
)


BASE_DIR = Path(__file__).resolve().parent
MANUAL_MD = BASE_DIR / "MANUAL_INSTALACION.md"
OUTPUT_PDF = BASE_DIR / "Manual_Instalacion_NemoOC.pdf"

AZUL = HexColor("#2563EB")
AZUL_SUAVE = HexColor("#DBEAFE")
GRIS = HexColor("#475569")
GRIS_CLARO = HexColor("#E2E8F0")
GRIS_FONDO = HexColor("#F8FAFC")

style_title = ParagraphStyle(
    "Title",
    fontName="Helvetica-Bold",
    fontSize=26,
    leading=31,
    textColor=AZUL,
    alignment=TA_CENTER,
    spaceAfter=10,
)
style_subtitle = ParagraphStyle(
    "Subtitle",
    fontName="Helvetica",
    fontSize=13,
    leading=18,
    textColor=GRIS,
    alignment=TA_CENTER,
    spaceAfter=8,
)
style_section = ParagraphStyle(
    "Section",
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=19,
    textColor=white,
    alignment=TA_CENTER,
)
style_h2 = ParagraphStyle(
    "H2",
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=AZUL,
    spaceBefore=10,
    spaceAfter=6,
)
style_body = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=10.8,
    leading=15,
    textColor=black,
    spaceAfter=6,
)
style_bullet = ParagraphStyle(
    "Bullet",
    fontName="Helvetica",
    fontSize=10.8,
    leading=15,
    textColor=black,
    leftIndent=16,
    firstLineIndent=-8,
    spaceAfter=3,
)
style_step = ParagraphStyle(
    "Step",
    fontName="Helvetica",
    fontSize=10.8,
    leading=15,
    textColor=black,
    leftIndent=16,
    spaceAfter=3,
)
style_code = ParagraphStyle(
    "Code",
    fontName="Courier",
    fontSize=9.5,
    leading=13,
    textColor=HexColor("#0F172A"),
    leftIndent=18,
    rightIndent=18,
    backColor=GRIS_FONDO,
    borderPadding=8,
    spaceAfter=8,
)
style_callout = ParagraphStyle(
    "Callout",
    fontName="Helvetica",
    fontSize=10.8,
    leading=15,
    textColor=HexColor("#0F172A"),
)


def format_inline(text: str) -> str:
    """Escapa texto simple y transforma segmentos entre backticks a monoespaciado."""
    parts = text.split("`")
    out: list[str] = []
    for idx, part in enumerate(parts):
        escaped = escape(part)
        if idx % 2 == 1:
            out.append(f'<font name="Courier">{escaped}</font>')
        else:
            out.append(escaped)
    return "".join(out)


def section_bar(text: str) -> Table:
    table = Table([[Paragraph(format_inline(text), style_section)]], colWidths=[6.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ]
        )
    )
    return table


def info_box(text: str) -> Table:
    table = Table([[Paragraph(format_inline(text), style_callout)]], colWidths=[6.55 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AZUL_SUAVE),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_CLARO),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [6, 6, 6, 6]),
            ]
        )
    )
    return table


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(GRIS_CLARO)
    canvas.line(doc.leftMargin, 0.55 * inch, letter[0] - doc.rightMargin, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#64748B"))
    canvas.drawString(doc.leftMargin, 0.35 * inch, "NemoOC Web | Manual actualizado 2026-04-03")
    canvas.drawRightString(letter[0] - doc.rightMargin, 0.35 * inch, f"Pagina {doc.page}")
    canvas.restoreState()


def parse_markdown_lines(lines: list[str]):
    story: list = []
    buffer: list[str] = []
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        if not buffer:
            return
        text = " ".join(part.strip() for part in buffer if part.strip()).strip()
        buffer.clear()
        if text:
            story.append(Paragraph(format_inline(text), style_body))

    for raw_line in lines:
        line = raw_line.rstrip()

        if in_code:
            if line.startswith("```"):
                story.append(XPreformatted("\n".join(code_lines), style_code))
                code_lines = []
                in_code = False
            else:
                code_lines.append(line)
            continue

        if line.startswith("```"):
            flush_paragraph()
            in_code = True
            code_lines = []
            continue

        if not line.strip():
            flush_paragraph()
            story.append(Spacer(1, 4))
            continue

        if line.startswith("## "):
            flush_paragraph()
            story.append(Spacer(1, 8))
            story.append(section_bar(line[3:].strip()))
            story.append(Spacer(1, 8))
            continue

        if line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(format_inline(line[4:].strip()), style_h2))
            continue

        if line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph(f"&bull; {format_inline(line[2:].strip())}", style_bullet))
            continue

        if re.match(r"^\d+\.\s+", line):
            flush_paragraph()
            story.append(Paragraph(format_inline(line.strip()), style_step))
            continue

        buffer.append(line)

    flush_paragraph()

    if in_code and code_lines:
        story.append(XPreformatted("\n".join(code_lines), style_code))

    return story


def build_pdf() -> str:
    if not MANUAL_MD.exists():
        raise FileNotFoundError(f"No existe el archivo fuente: {MANUAL_MD}")

    raw_text = MANUAL_MD.read_text(encoding="utf-8")
    lines = raw_text.splitlines()

    title = "NemoOC Web"
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()

    first_section_idx = next((idx for idx, line in enumerate(lines) if line.startswith("## ")), len(lines))
    meta_lines = [line.strip() for line in lines[1:first_section_idx] if line.strip()]
    body_lines = lines[first_section_idx:]

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )

    story: list = []
    story.append(Spacer(1, 1.1 * inch))
    story.append(Paragraph(format_inline(title), style_title))
    story.append(Paragraph("Manual de uso y configuracion del sistema actual", style_subtitle))
    story.append(Spacer(1, 0.15 * inch))

    for line in meta_lines:
        story.append(Paragraph(format_inline(line), style_subtitle))

    story.append(Spacer(1, 0.35 * inch))
    story.append(
        info_box(
            "Este manual esta pensado para la version web actual. "
            "Explica el flujo operativo del sistema y deja especialmente clara la configuracion de holdings."
        )
    )
    story.append(Spacer(1, 0.35 * inch))
    story.append(
        info_box(
            "Resumen rapido: Configuracion carga parametros generales. "
            "Holdings administra privados. Importar baja OCs publicas y sincroniza OCs privadas."
        )
    )
    story.append(PageBreak())

    story.extend(parse_markdown_lines(body_lines))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"PDF generado: {OUTPUT_PDF}")
    return str(OUTPUT_PDF)


if __name__ == "__main__":
    build_pdf()
