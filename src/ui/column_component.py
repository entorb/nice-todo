"""Droppable column component for the TODO board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from src.ui._shared import (
    _COLOR_COLUMN_BG,
    _COLOR_COLUMN_HIGHLIGHT,
    _EVENT_KEYDOWN_ENTER,
    _OPACITY_COLUMN_DELETE,
)
from src.ui.card_component import CardComponent

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Column, Label

# Module-level drag state for columns
dragged_column: ColumnComponent | None = None


class ColumnComponent(ui.column):
    """Droppable column with header, card list, and card input field."""

    def __init__(  # noqa: PLR0913
        self,
        column: Column,
        labels: list[Label] | None = None,
        *,
        on_rename: Callable[[int, str], None] | None = None,
        on_add_card: Callable[[int, str], None] | None = None,
        on_delete_column: Callable[[int], None] | None = None,
        on_drop_card: Callable[[int, int, int], None] | None = None,
        on_drop_column: Callable[[int, int], None] | None = None,
        card_callbacks: dict | None = None,
        bulk_mode: bool = False,
    ) -> None:
        """Initialize column component."""
        super().__init__()
        self.column_data = column
        self._on_rename = on_rename
        self._on_add_card = on_add_card
        self._on_delete_column = on_delete_column
        self._on_drop_card = on_drop_card
        self._on_drop_column = on_drop_column

        labels_map: dict[int, Label] = {}
        if labels:
            labels_map = {lb.id: lb for lb in labels if lb.id is not None}

        with self.classes("rounded-lg board-col").style(
            "min-width:280px;max-width:320px;gap:3px;"
            f"background:{_COLOR_COLUMN_BG};padding:12px;border-radius:10px;"
        ):
            # Column header
            with ui.row().classes("items-center w-full no-wrap gap-0"):
                # Drag handle
                ui.icon("drag_indicator", size="sm").classes(
                    "cursor-move text-grey-5"
                ).props("draggable").on("dragstart", self._handle_col_dragstart)

                # Editable column name
                name_input = (
                    ui.input(value=column.name)
                    .classes("flex-grow")
                    .props("dense borderless")
                    .style("font-weight:600;font-size:0.95rem;")
                )
                name_input.on(
                    _EVENT_KEYDOWN_ENTER,
                    lambda _e, inp=name_input, cid=column.id: (
                        self._on_rename(cid, inp.value)  # type: ignore[misc]
                        if self._on_rename and inp.value
                        else None
                    ),
                )
                name_input.on(
                    "blur",
                    lambda _e, inp=name_input, cid=column.id: (
                        self._on_rename(cid, inp.value)  # type: ignore[misc]
                        if self._on_rename and inp.value
                        else None
                    ),
                )

                # Delete column button
                ui.button(
                    icon="delete_outline",
                    on_click=lambda _, cid=column.id: (
                        self._on_delete_column(cid)  # type: ignore[misc]
                        if self._on_delete_column
                        else None
                    ),
                ).props("flat dense round size=sm").classes("text-grey-5").style(
                    _OPACITY_COLUMN_DELETE
                ).tooltip("Delete column")

            # Card list
            for card in column.cards:
                card_label = labels_map.get(card.label_id) if card.label_id else None
                CardComponent(
                    card,
                    label=card_label,
                    bulk_mode=bulk_mode,
                    **(card_callbacks or {}),
                )

            # Add card input
            add_input = (
                ui.input(placeholder="+ Add a card…")
                .classes(f"w-full add-card-input-col-{column.id}")
                .props("dense borderless")
                .style(
                    "min-height:32px;background:rgba(255,255,255,0.5);"
                    "border-radius:6px;padding:2px 8px;font-size:0.85rem;"
                )
            )
            add_input.on(
                _EVENT_KEYDOWN_ENTER,
                lambda _e, inp=add_input, cid=column.id: self._handle_add_card(
                    inp, cid
                ),
            )

        # Drop events
        self.on("dragover.prevent", self._highlight)
        self.on("dragleave", self._unhighlight)
        self.on("drop", self._handle_drop)

    def _handle_col_dragstart(self) -> None:
        global dragged_column  # noqa: PLW0603
        dragged_column = self

    def _highlight(self) -> None:
        self.style(f"background:{_COLOR_COLUMN_HIGHLIGHT};")

    def _unhighlight(self) -> None:
        self.style(f"background:{_COLOR_COLUMN_BG};")

    def _handle_drop(self) -> None:
        global dragged_column  # noqa: PLW0603
        import src.ui.card_component as _card_mod  # noqa: PLC0415

        self._unhighlight()

        if dragged_column is not None and dragged_column is not self:
            if self._on_drop_column:
                self._on_drop_column(
                    dragged_column.column_data.id,  # type: ignore[arg-type]
                    self.column_data.id,  # type: ignore[arg-type]
                )
            dragged_column = None
            return

        dragged_column = None

        if _card_mod.dragged is None:
            return

        target_index = len(self.column_data.cards)
        if (
            _card_mod.drop_target is not None
            and _card_mod.drop_target.parent_slot is not None
            and _card_mod.drop_target.parent_slot.parent is self
        ):
            target_index = self.default_slot.children.index(_card_mod.drop_target)

        _card_mod.dragged.move(target_container=self, target_index=target_index)

        if self._on_drop_card:
            self._on_drop_card(
                _card_mod.dragged.card_data.id,  # type: ignore[arg-type]
                self.column_data.id,  # type: ignore[arg-type]
                target_index,
            )

        _card_mod.dragged = None
        _card_mod.drop_target = None

    def _handle_add_card(self, inp: ui.input, column_id: int | None) -> None:
        title = inp.value.strip() if inp.value else ""
        if not title:
            return
        if self._on_add_card and column_id is not None:
            self._on_add_card(column_id, title)
        inp.value = ""
