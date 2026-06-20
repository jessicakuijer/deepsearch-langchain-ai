"""Formatage du contenu rapport — tableaux en cartes responsive."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Union


@dataclass
class TextSegment:
    content: str


@dataclass
class TableSegment:
    headers: list[str]
    rows: list[list[str]]


ReportSegment = Union[TextSegment, TableSegment]


def _is_table_row(line: str) -> bool:
    if "\t" not in line:
        return False
    parts = [p.strip() for p in line.split("\t") if p.strip()]
    return len(parts) >= 3


def _escape_md_cell(value: str) -> str:
    return value.replace("|", "\\|").strip()


def _rows_to_markdown(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    padded = [r + [""] * (width - len(r)) for r in rows]
    header = padded[0]
    body = padded[1:] if len(padded) > 1 else []
    lines = [
        "| " + " | ".join(_escape_md_cell(c) for c in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(_escape_md_cell(c) for c in row) + " |")
    return "\n".join(lines)


def normalize_tabular_blocks(text: str) -> str:
    if not text or "\t" not in text:
        return text

    lines = text.splitlines()
    output: list[str] = []
    buffer: list[list[str]] = []
    expected_cols: int | None = None

    def flush() -> None:
        nonlocal buffer, expected_cols
        if buffer:
            output.append(_rows_to_markdown(buffer))
            output.append("")
        buffer = []
        expected_cols = None

    for line in lines:
        if _is_table_row(line):
            parts = [p.strip() for p in line.split("\t")]
            col_count = len(parts)
            if buffer and expected_cols and abs(col_count - expected_cols) > 1:
                flush()
            buffer.append(parts)
            expected_cols = col_count if expected_cols is None else expected_cols
        else:
            flush()
            output.append(line)
    flush()
    return "\n".join(output).strip()


def _is_pipe_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _is_separator_row(line: str) -> bool:
    return bool(re.match(r"^\|[-:\s|]+\|\s*$", line.strip()))


def _parse_pipe_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    return [cell.strip() for cell in inner.split("|")]


def parse_report_segments(text: str) -> list[ReportSegment]:
    normalized = normalize_tabular_blocks(text or "")
    if not normalized:
        return [TextSegment("_Aucun contenu disponible._")]

    lines = normalized.splitlines()
    segments: list[ReportSegment] = []
    text_buf: list[str] = []
    index = 0

    def flush_text() -> None:
        if text_buf:
            chunk = "\n".join(text_buf).strip()
            if chunk:
                segments.append(TextSegment(chunk))
            text_buf.clear()

    while index < len(lines):
        line = lines[index]
        if (
            _is_pipe_row(line)
            and index + 1 < len(lines)
            and _is_separator_row(lines[index + 1])
        ):
            flush_text()
            headers = _parse_pipe_row(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and _is_pipe_row(lines[index]):
                rows.append(_parse_pipe_row(lines[index]))
                index += 1
            if headers and rows:
                width = len(headers)
                normalized_rows = [row + [""] * (width - len(row)) for row in rows]
                segments.append(TableSegment(headers=headers, rows=normalized_rows))
            continue

        text_buf.append(line)
        index += 1

    flush_text()
    return segments or [TextSegment(normalized)]


def format_inline_markdown(text: str) -> str:
    """Échappe le HTML puis convertit le gras markdown (**…**)."""
    escaped = html.escape(text or "")
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def render_table_cards(headers: list[str], rows: list[list[str]]) -> str:
    parts = ['<div class="ds-card-table">']
    for row in rows:
        title = format_inline_markdown(row[0]) if row else ""
        parts.append('<div class="ds-card-table-item">')
        parts.append(f'<div class="ds-card-table-title">{title}</div>')
        for col_index in range(1, len(headers)):
            label = html.escape(headers[col_index])
            value = format_inline_markdown(row[col_index]) if col_index < len(row) else ""
            if not value:
                continue
            parts.append(
                f'<div class="ds-card-table-field">'
                f'<span class="ds-card-table-label">{label}</span>'
                f'<span class="ds-card-table-value">{value}</span>'
                f"</div>"
            )
        parts.append("</div>")
    parts.append("</div>")
    return "".join(parts)
