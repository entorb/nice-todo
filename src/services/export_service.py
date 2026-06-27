"""Card export — module-level functions."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from src.services.sort import card_sort_by_prio_label_name

if TYPE_CHECKING:
    from src.models import Board, Card, Label


def _prepare_export_data(
    board: Board,
    labels: list[Label],
    *,
    completed_only: bool,
) -> tuple[dict[int | None, str], list[tuple[str, list[Card]]]]:
    label_map = {lb.id: lb.name for lb in labels if lb.id is not None}
    key_fn = card_sort_by_prio_label_name(label_map)
    columns = []
    for col in board.columns:
        cards = (
            [c for c in col.cards if c.is_completed]
            if completed_only
            else list(col.cards)
        )
        if not cards:
            continue
        cards.sort(key=key_fn)
        columns.append((col.name, cards))
    return label_map, columns


def _format_card(
    card: Card,
    label_map: dict[int | None, str],
    *,
    completed_only: bool,
    fmt: str,
) -> str:
    """Format single card line for txt, markdown, or html."""
    if fmt == "html":
        title = escape(card.title)
        lbl = (
            f" <em>({escape(label_map[card.label_id])})</em>"
            if card.label_id and card.label_id in label_map
            else ""
        )
        prio = (
            ' <span style="color:red;" title="Important">⚑</span>'
            if card.prio is True
            else ""
        )
        if completed_only:
            return (
                f'  <li><input type="checkbox" checked disabled>'
                f" {title}{lbl}{prio}</li>"
            )
        checked = " checked" if card.is_completed else ""
        return (
            f'  <li><input type="checkbox"{checked} disabled> {title}{lbl}{prio}</li>'
        )

    suffix = ""
    if card.label_id and card.label_id in label_map:
        suffix = f" ({label_map[card.label_id]})"
    if card.prio is True:
        suffix += " ⚑" if fmt == "markdown" else " *"

    if completed_only:
        prefix = "" if fmt == "txt" else "- "
    else:
        check = "x" if card.is_completed else " "
        prefix = f"[{check}] " if fmt == "txt" else f"- [{check}] "

    return f"{prefix}{card.title}{suffix}"


def export(
    board: Board,
    labels: list[Label],
    *,
    completed_only: bool = False,
    fmt: str = "markdown",
) -> str:
    """Export cards in chosen format."""
    label_map, columns = _prepare_export_data(
        board, labels, completed_only=completed_only
    )

    if fmt == "html":
        parts = [f"<h2>{escape(board.name)}</h2>"]
        for col_name, cards in columns:
            parts.append(f"<h3>{escape(col_name)}</h3>")
            parts.append("<ul>")
            parts.extend(
                _format_card(c, label_map, completed_only=completed_only, fmt="html")
                for c in cards
            )
            parts.append("</ul>")
        return "\n".join(parts) + "\n"

    if fmt == "markdown":
        lines = [f"## {board.name}", ""]
        for col_name, cards in columns:
            lines.append(f"### {col_name}")
            lines.extend(
                _format_card(
                    c, label_map, completed_only=completed_only, fmt="markdown"
                )
                for c in cards
            )
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"

    # txt
    lines = []
    for col_name, cards in columns:
        lines.append(col_name)
        lines.extend(
            _format_card(c, label_map, completed_only=completed_only, fmt="txt")
            for c in cards
        )
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
