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


def card_sort_key(
    label_map: dict[int | None, str],
) -> Callable:
    """Return a sort-key function for cards."""

    def key(c: Card) -> tuple[bool, int, bool, str, str]:
        if c.is_completed:
            return (
                True,  # 1 completed
                _prio_rank(c),  # 2 prio
                False,  # 3 has label
                c.date_completed.isoformat()
                if c.date_completed
                else "",  # 4 date completed
                "",  # 5 none
            )
        label_name = label_map.get(c.label_id, "") if c.label_id else ""  # type: ignore[arg-type]
        return (
            False,  # 1 completed
            _prio_rank(c),  # 2 prio
            not bool(label_name),  # 3 label: has label before no label
            label_name.lower(),  # 4 label name
            c.title.lower(),  # 5 card title
            # c.date_created.isoformat(),  # 5 date
        )

    return key
