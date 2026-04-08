"""Markdown export service for the TODO Board."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Board, Label


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
            for card in cards:
                suffix = (
                    f" ({label_map[card.label_id]})"
                    if card.label_id and card.label_id in label_map
                    else ""
                )
                prefix = (
                    "- "
                    if completed_only
                    else f"- [{'x' if card.is_completed else ' '}] "
                )
                lines.append(f"{prefix}{card.title}{suffix}")
            lines.append("")
        return "\n".join(lines).rstrip("\n") + "\n"
