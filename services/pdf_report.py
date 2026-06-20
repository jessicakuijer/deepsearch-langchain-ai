"""Génération PDF structurée pour les rapports DeepSearch."""

from __future__ import annotations

import html
import os
import re
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ui.report_format import TableSegment, parse_report_segments

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 54
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

BRAND_DARK = colors.HexColor("#16201C")
BRAND_GREEN = colors.HexColor("#2E4538")
BRAND_MUTED = colors.HexColor("#8A938D")
BRAND_BODY = colors.HexColor("#2B332E")
BRAND_CREAM = colors.HexColor("#FBFAF5")
BRAND_BORDER = colors.HexColor("#E4DFD0")


def _inline_md_to_pdf(text: str) -> str:
    escaped = html.escape(text or "")
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", escaped)
    return escaped


def _is_special_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("#"):
        return True
    if re.match(r"^[-*]\s+", stripped):
        return True
    if re.match(r"^\d+\.\s+", stripped):
        return True
    return False


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "label": ParagraphStyle(
            "PdfLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=BRAND_MUTED,
            spaceAfter=6,
            alignment=TA_CENTER,
            letterSpacing=1.2,
        ),
        "title": ParagraphStyle(
            "PdfTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=26,
            spaceAfter=10,
            alignment=TA_CENTER,
            textColor=BRAND_DARK,
        ),
        "meta": ParagraphStyle(
            "PdfMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=BRAND_BODY,
            spaceAfter=4,
            alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "PdfSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            spaceBefore=16,
            spaceAfter=8,
            textColor=BRAND_GREEN,
        ),
        "h3": ParagraphStyle(
            "PdfH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            spaceBefore=14,
            spaceAfter=6,
            textColor=BRAND_DARK,
        ),
        "body": ParagraphStyle(
            "PdfBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            textColor=BRAND_BODY,
        ),
        "bullet": ParagraphStyle(
            "PdfBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=4,
            textColor=BRAND_BODY,
        ),
        "card_title": ParagraphStyle(
            "PdfCardTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceAfter=2,
            textColor=BRAND_DARK,
        ),
        "card_field": ParagraphStyle(
            "PdfCardField",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
            textColor=BRAND_BODY,
        ),
        "footer": ParagraphStyle(
            "PdfFooter",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
            textColor=BRAND_MUTED,
        ),
    }


def _text_segment_to_flowables(text: str, styles: dict[str, ParagraphStyle]) -> list:
    flowables: list = []
    lines = text.splitlines()
    bullet_buf: list[str] = []
    index = 0

    def flush_bullets() -> None:
        for item in bullet_buf:
            flowables.append(
                Paragraph(f"• {_inline_md_to_pdf(item)}", styles["bullet"])
            )
        bullet_buf.clear()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()

        if not stripped:
            flush_bullets()
            flowables.append(Spacer(1, 4))
            index += 1
            continue

        if stripped.startswith("### "):
            flush_bullets()
            flowables.append(Paragraph(_inline_md_to_pdf(stripped[4:]), styles["h3"]))
        elif stripped.startswith("## "):
            flush_bullets()
            flowables.append(Paragraph(_inline_md_to_pdf(stripped[3:]), styles["section"]))
        elif stripped.startswith("# "):
            flush_bullets()
            flowables.append(Paragraph(_inline_md_to_pdf(stripped[2:]), styles["section"]))
        elif re.match(r"^[-*]\s+", stripped):
            bullet_buf.append(re.sub(r"^[-*]\s+", "", stripped))
        elif re.match(r"^\d+\.\s+", stripped):
            flush_bullets()
            flowables.append(
                Paragraph(_inline_md_to_pdf(re.sub(r"^\d+\.\s+", "", stripped)), styles["body"])
            )
        else:
            flush_bullets()
            paragraph_lines = [stripped]
            while index + 1 < len(lines):
                nxt = lines[index + 1].strip()
                if not nxt or _is_special_line(lines[index + 1]):
                    break
                index += 1
                paragraph_lines.append(nxt)
            flowables.append(
                Paragraph(_inline_md_to_pdf(" ".join(paragraph_lines)), styles["body"])
            )

        index += 1

    flush_bullets()
    return flowables


def _table_segment_to_flowables(segment: TableSegment, styles: dict[str, ParagraphStyle]) -> list:
    flowables: list = []

    for row in segment.rows:
        card_rows: list[list] = []
        title = row[0] if row else ""
        card_rows.append(
            [Paragraph(_inline_md_to_pdf(f"**{title}**"), styles["card_title"])]
        )

        for col_index in range(1, len(segment.headers)):
            label = segment.headers[col_index].strip()
            value = row[col_index].strip() if col_index < len(row) else ""
            if not label or not value:
                continue
            card_rows.append(
                [
                    Paragraph(
                        f"<b>{html.escape(label)}</b><br/>{_inline_md_to_pdf(value)}",
                        styles["card_field"],
                    )
                ]
            )

        card = Table(card_rows, colWidths=[CONTENT_WIDTH])
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), BRAND_CREAM),
                    ("BOX", (0, 0), (-1, -1), 0.75, BRAND_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        flowables.append(card)
        flowables.append(Spacer(1, 8))

    return flowables


def _build_header(
    query: str,
    *,
    duration_s: int,
    sources_count: int,
    attempt_count: int,
    styles: dict[str, ParagraphStyle],
) -> list:
    worker_model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    return [
        Paragraph("RAPPORT DE RECHERCHE", styles["label"]),
        Spacer(1, 2),
        Paragraph(_inline_md_to_pdf(query.strip()), styles["title"]),
        Spacer(1, 6),
        HRFlowable(width="100%", thickness=1.5, color=BRAND_GREEN, spaceBefore=0, spaceAfter=10),
        Paragraph(f"Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles["meta"]),
        Paragraph(
            f"Durée : {duration_s} s · Sources : {sources_count} · Modèle : {worker_model} · {attempt_count} tentative(s)",
            styles["meta"],
        ),
        Spacer(1, 14),
    ]


def build_pdf_report(
    query: str,
    report_content: str,
    *,
    duration_s: int = 0,
    sources_count: int = 0,
    attempt_count: int = 1,
) -> bytes:
    styles = _pdf_styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=48,
        bottomMargin=42,
        title="Rapport DeepSearch",
        author="DeepSearch",
    )

    story: list = _build_header(
        query,
        duration_s=duration_s,
        sources_count=sources_count,
        attempt_count=attempt_count,
        styles=styles,
    )
    story.append(Paragraph("Résultats", styles["section"]))
    story.append(Spacer(1, 4))

    for segment in parse_report_segments(report_content):
        if isinstance(segment, TableSegment):
            story.extend(_table_segment_to_flowables(segment, styles))
        else:
            story.extend(_text_segment_to_flowables(segment.content, styles))

    story.extend(
        [
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=0.75, color=BRAND_BORDER, spaceBefore=4, spaceAfter=10),
            Paragraph("Méthodologie", styles["section"]),
            Paragraph(
                _inline_md_to_pdf(
                    "Ce rapport a été généré par l'agent DeepSearch à partir de recherches web, "
                    "Wikipédia, navigation et analyse Python. Vérifiez les informations avant toute décision."
                ),
                styles["footer"],
            ),
        ]
    )

    doc.build(story)
    return buffer.getvalue()
