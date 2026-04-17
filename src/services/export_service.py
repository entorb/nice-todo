"""Markdown and HTML export service for the Nice TODO."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

from src.services.sort import card_sort_key

if TYPE_CHECKING:
    from src.models import Board, Card, Label


class ExportService:
    """Generate Markdown or HTML exports from board data."""

    def export(
        self,
        board: Board,
        labels: list[Label],
        *,
        completed_only: bool = False,
        fmt: str = "markdown",
    ) -> str:
        """Export cards in the chosen format."""
        if fmt == "html":
            return self._export_html(board, labels, completed_only=completed_only)
        return self._export_markdown(board, labels, completed_only=completed_only)

    def _export_markdown(
        self,
        board: Board,
        labels: list[Label],
        *,
        completed_only: bool = False,
    ) -> str:
        """Export cards as markdown."""
        label_map: dict[int | None, str] = {
            lb.id: lb.name for lb in labels if lb.id is not None
        }
        key_fn = card_sort_key(label_map)
        lines = [f"## {board.name}", ""]
        for col in board.columns:
            cards = (
                [c for c in col.cards if c.is_completed]
                if completed_only
                else list(col.cards)
            )
            if not cards:
                continue
            cards.sort(key=key_fn)
            lines.append(f"### {col.name}")
            lines.extend(
                self._format_card_md(card, label_map, completed_only=completed_only)
                for card in cards
            )
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"

    def _export_html(
        self,
        board: Board,
        labels: list[Label],
        *,
        completed_only: bool = False,
    ) -> str:
        """Export cards as HTML."""
        label_map: dict[int | None, str] = {
            lb.id: lb.name for lb in labels if lb.id is not None
        }
        key_fn = card_sort_key(label_map)
        parts = [f"<h2>{escape(board.name)}</h2>"]
        for col in board.columns:
            cards = (
                [c for c in col.cards if c.is_completed]
                if completed_only
                else list(col.cards)
            )
            if not cards:
                continue
            cards.sort(key=key_fn)
            parts.append(f"<h3>{escape(col.name)}</h3>")
            parts.append("<ul>")
            parts.extend(
                self._format_card_html(card, label_map, completed_only=completed_only)
                for card in cards
            )
            parts.append("</ul>")
        return "\n".join(parts) + "\n"

    @staticmethod
    def _format_card_md(
        card: Card,
        label_map: dict[int | None, str],
        *,
        completed_only: bool,
    ) -> str:
        """Format a single card as a markdown line."""
        suffix = ""
        if card.label_id and card.label_id in label_map:
            suffix = f" ({label_map[card.label_id]})"

        if card.prio is True:
            suffix += " ⚑"

        if completed_only:
            prefix = "- "
        else:
            check = "x" if card.is_completed else " "
            prefix = f"- [{check}] "

        return f"{prefix}{card.title}{suffix}"

    @staticmethod
    def _format_card_html(
        card: Card,
        label_map: dict[int | None, str],
        *,
        completed_only: bool,
    ) -> str:
        """Format a single card as an HTML list item with checkbox."""
        title = escape(card.title)
        suffix = ""
        if card.label_id and card.label_id in label_map:
            suffix = f" <em>({escape(label_map[card.label_id])})</em>"

        if card.prio is True:
            suffix += ' <span style="color:red;" title="Important">⚑</span>'

        if completed_only:
            return (
                f'  <li><input type="checkbox" checked disabled> {title}{suffix}</li>'
            )

        checked = " checked" if card.is_completed else ""
        return f'  <li><input type="checkbox"{checked} disabled> {title}{suffix}</li>'
