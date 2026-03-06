"""
Report formatting helpers for Telegram.

FR-037: Monospace tables with Unicode box-drawing for daily, weekly, monthly reports.
Uses parse_mode="HTML" with <pre> blocks for alignment.
"""

from __future__ import annotations

import html
from typing import Sequence

MAX_TITLE_LEN = 40


def _truncate(text: str, max_len: int = MAX_TITLE_LEN) -> str:
    """Truncate text to max_len, adding ellipsis if needed."""
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rstrip() + "..."


def escape_for_html(text: str) -> str:
    """Escape user content for HTML (inside <pre> blocks)."""
    return html.escape(text or "", quote=False)


def build_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    col_widths: Sequence[int] | None = None,
    escape: bool = True,
) -> str:
    """
    Build a monospace table with Unicode box-drawing.

    Args:
        headers: Column headers
        rows: Data rows (each row is a sequence of cell values)
        col_widths: Optional fixed widths per column; auto-computed if None
        escape: Whether to escape cell content for HTML

    Returns:
        Table string (plain text, to be wrapped in <pre> by caller)
    """
    if not headers:
        return ""

    def _cell(val: str, width: int) -> str:
        s = _truncate(val or "", width)
        s = escape_for_html(s) if escape else s
        return s.ljust(width)

    # Compute column widths
    if col_widths:
        widths = list(col_widths)
    else:
        widths = []
        for i, h in enumerate(headers):
            w = len(h)
            for row in rows:
                if i < len(row):
                    w = max(w, min(MAX_TITLE_LEN, len(str(row[i]))))
            widths.append(max(3, w))

    def _sep(left: str, mid: str, right: str) -> str:
        parts = [left]
        for i, w in enumerate(widths):
            parts.append("─" * w)
            if i < len(widths) - 1:
                parts.append(mid)
        parts.append(right)
        return "".join(parts)

    def _row(cells: Sequence[str]) -> str:
        padded = []
        for i, w in enumerate(widths):
            val = cells[i] if i < len(cells) else ""
            padded.append(_cell(val, w))
        return "│ " + " │ ".join(padded) + " │"

    lines = []
    lines.append(_sep("┌", "┬", "┐"))
    lines.append(_row([str(h) for h in headers]))
    lines.append(_sep("├", "┼", "┤"))
    for row in rows:
        lines.append(_row([str(c) for c in row]))
    lines.append(_sep("└", "┴", "┘"))
    return "\n".join(lines)


def wrap_pre(text: str) -> str:
    """Wrap in <pre> for HTML parse_mode. Cell content already escaped by build_table."""
    return f"<pre>{text}</pre>"
