"""Markdown export service for the Nice TODO."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Board, Card, Label


class ExportService:
    """Generate Markdown exports from board data."""

    def export(
        self,
        board: Board,
        labels: list[Label],
        *,
        completed_only: bool = False,
    ) -> str:
        """Export cards as markdown, optionally filtering to completed only."""
        label_map = {lb.id: lb.name for lb in labels if lb.id is not None}
        lines = [f"## {board.name}", ""]
        for col in board.columns:
            cards = (
                [c for c in col.cards if c.is_completed]
                if completed_only
                else list(col.cards)
            )
            if not cards:
                continue
            cards.sort(key=lambda c: c.position)
            lines.append(f"### {col.name}")
            lines.extend(
                self._format_card(card, label_map, completed_only=completed_only)
                for card in cards
            )
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"

    @staticmethod
    def _format_card(
        card: Card,
        label_map: dict[int | None, str],
        *,
        completed_only: bool,
    ) -> str:
        """Format a single card as a markdown line."""
        suffix = ""
        if card.label_id and card.label_id in label_map:
            suffix = f" ({label_map[card.label_id]})"

        if completed_only:
            prefix = "- "
        else:
            check = "x" if card.is_completed else " "
            prefix = f"- [{check}] "

        return f"{prefix}{card.title}{suffix}"
