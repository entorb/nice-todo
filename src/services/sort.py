"""Shared card sorting logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Card


def _prio_rank(card: Card) -> int:
    """Rank prio: True=0, None=1, False=2."""
    if card.prio is True:
        return 0
    if card.prio is None:
        return 1
    return 2


def card_sort_key(
    label_map: dict[int | None, str],
) -> callable:
    """Return a sort-key function for cards."""

    def key(c: Card) -> tuple[bool, int, bool, str, str]:
        if c.is_completed:
            return (
                True,
                _prio_rank(c),
                False,
                c.date_completed.isoformat() if c.date_completed else "",
                "",
            )
        label_name = label_map.get(c.label_id, "") if c.label_id else ""  # type: ignore[arg-type]
        return (
            False,
            _prio_rank(c),
            not bool(label_name),  # False (has label) sorts before True (no label)
            label_name,
            c.date_created.isoformat(),
        )

    return key
