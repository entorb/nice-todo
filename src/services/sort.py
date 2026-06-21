"""Shared card sorting logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Card


def _prio_rank(card: Card) -> int:
    """Rank prio: True=0, None=1, False=2."""
    if card.prio is True:
        return 0
    if card.prio is None:
        return 1
    return 2


def card_sort_by_prio_label_name(
    label_map: dict[int | None, str],
) -> Callable:
    """Return a sort-key function for cards."""

    def key(c: Card) -> tuple[bool, int, str, str]:
        label_name = label_map.get(c.label_id, "") if c.label_id else ""  # type: ignore[arg-type]
        return (
            c.is_completed,  # 1 completed
            _prio_rank(c),  # 2 prio
            label_name.lower(),  # 3 label
            c.title.lower(),  # 4 title
        )

    return key


def card_sort_by_date() -> Callable:
    """Sort-key: not completed by date_created ASC, completed by date_completed ASC."""

    def key(c: Card) -> tuple[bool, str]:
        return (
            c.is_completed,  # 1 completed
            c.date_completed.isoformat()  # 2 date completed or created
            if c.date_completed
            else c.date_created.isoformat(),
        )

    return key
