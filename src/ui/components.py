"""
Reusable UI components for the TODO board.

Provides LabelBadge, CardComponent (draggable), and ColumnComponent (droppable)
following the drag-and-drop pattern from the prototype in src/draganddrop.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Card, Column, Label

# Shared constants
_EVENT_KEYDOWN_ENTER = "keydown.enter"
_ICON_BTN_OPACITY = "opacity:0.6;"
_ICON_BTN_PROPS = "flat dense round size=xs"
_LUMINANCE_THRESHOLD = 0.45
_OPACITY_COLUMN_DELETE = "opacity:0.5;"
_OPACITY_COMPLETED_LABELED = "opacity:0.45;"
_OPACITY_COMPLETED_PLAIN = "opacity:0.5;"

# Colors
_COLOR_CARD_BG = "white"
_COLOR_CARD_COMPLETED_BG = "#f5f5f5"
_COLOR_COLUMN_BG = "#eceff1"
_COLOR_COLUMN_HIGHLIGHT = "#cfd8dc"
_COLOR_TEXT_DARK = "#222"
_COLOR_TEXT_LIGHT = "#fff"

# Module-level drag state
dragged: CardComponent | None = None
drop_target: CardComponent | None = None
dragged_column: ColumnComponent | None = None


# CardComponent
def _contrast_color(hex_color: str) -> str:
    """Return black or white text color based on background luminance."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:  # noqa: PLR2004
        hex_color = "".join(c * 2 for c in hex_color)
    r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    # Perceived luminance (ITU-R BT.601)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return _COLOR_TEXT_DARK if luminance > _LUMINANCE_THRESHOLD else _COLOR_TEXT_LIGHT


class CardComponent(ui.card):
    """Draggable card with checkbox, title, label picker, and delete button."""

    def __init__(  # noqa: PLR0913
        self,
        card: Card,
        label: Label | None = None,
        *,
        on_toggle_completed: Callable[[int, bool], None] | None = None,
        on_toggle_template: Callable[[int, bool], None] | None = None,
        on_edit_title: Callable[[int, str], None] | None = None,
        on_delete: Callable[[int], None] | None = None,
        on_select: Callable[[int, bool], None] | None = None,
        on_set_label: Callable[[int, int | None], None] | None = None,
        on_move_copy: Callable[[int, str], None] | None = None,
        available_labels: list[Label] | None = None,
        bulk_mode: bool = False,
    ) -> None:
        """Initialize card component."""
        super().__init__()
        self.card_data = card
        self._on_toggle_completed = on_toggle_completed
        self._on_toggle_template = on_toggle_template
        self._on_edit_title = on_edit_title
        self._on_delete = on_delete
        self._on_select = on_select
        self._on_set_label = on_set_label
        self._on_move_copy = on_move_copy

        style = self._compute_style(card, label)
        text_color = _contrast_color(label.color) if label else _COLOR_TEXT_DARK
        color_class = "card-dark" if text_color == _COLOR_TEXT_DARK else "card-light"

        with (
            self.classes(f"w-full cursor-pointer {color_class}").style(style),
            ui.row().classes("items-center w-full no-wrap gap-1"),
        ):
            self._build_drag_handle()
            self._build_checkboxes(card, bulk_mode=bulk_mode)
            self._build_title(card)
            self._build_action_buttons(card, available_labels)

        # Drag events
        self.on("dragstart", self._handle_dragstart)
        self.on("dragend", lambda: self.props(remove="draggable"))
        self.on("dragover.prevent", self._handle_dragover)

    @staticmethod
    def _compute_style(card: Card, label: Label | None) -> str:
        """Compute the card's inline CSS style string."""
        style = (
            "min-height:30px;padding:2px 8px;border-radius:6px;"
            "transition:box-shadow 0.15s,opacity 0.15s;"
        )
        if label is not None:
            text_color = _contrast_color(label.color)
            style += f"background:{label.color};color:{text_color};"
            if card.is_completed:
                style += _OPACITY_COMPLETED_LABELED
        elif card.is_completed:
            style += (
                f"background:{_COLOR_CARD_COMPLETED_BG};"
                f"{_OPACITY_COMPLETED_PLAIN}color:{_COLOR_TEXT_DARK};"
            )
        else:
            style += f"background:{_COLOR_CARD_BG};color:{_COLOR_TEXT_DARK};"

        return style

    def _build_drag_handle(self) -> None:
        """Build the drag-handle icon."""
        handle = (
            ui.icon("drag_indicator").classes("cursor-grab").style("font-size:1.1rem;")
        )
        handle.on("mousedown", lambda: self.props("draggable"))
        handle.on("mouseup", lambda: self.props(remove="draggable"))

    def _build_checkboxes(self, card: Card, *, bulk_mode: bool) -> None:
        """Build bulk-selection and completion checkboxes."""
        if bulk_mode:
            ui.checkbox(
                value=False,
                on_change=lambda e, cid=card.id: (
                    self._on_select(cid, e.value)  # type: ignore[misc]
                    if self._on_select
                    else None
                ),
            ).classes("min-w-[24px] min-h-[24px]").props("dense")

        check_opacity = "" if card.is_completed else _ICON_BTN_OPACITY
        ui.checkbox(
            value=card.is_completed,
            on_change=lambda e, cid=card.id: (
                self._on_toggle_completed(cid, e.value)  # type: ignore[misc]
                if self._on_toggle_completed
                else None
            ),
        ).classes("min-w-[24px] min-h-[24px]").props("dense color=green").style(
            check_opacity
        ).tooltip("Toggle completed")

    def _build_title(self, card: Card) -> None:
        """Build the editable title input."""
        title_input = (
            ui.input(value=card.title)
            .classes("flex-grow cursor-text")
            .props("dense borderless autogrow")
            .style("font-size:0.9rem;word-wrap:break-word;")
        )

        def on_commit(
            _e: object,
            inp: ui.input = title_input,
            cid: int | None = card.id,
        ) -> None:
            if self._on_edit_title and inp.value:
                self._on_edit_title(cid, inp.value)  # type: ignore[arg-type]

        title_input.on(_EVENT_KEYDOWN_ENTER, on_commit)
        title_input.on("blur", on_commit)

    def _build_action_buttons(
        self,
        card: Card,
        available_labels: list[Label] | None,
    ) -> None:
        """Build template toggle, label picker, move, and delete buttons."""
        # Label picker
        if available_labels and self._on_set_label:
            self._build_label_picker(card, available_labels)

        # Template toggle
        pin_opacity = "" if card.is_template else _ICON_BTN_OPACITY
        ui.button(
            icon="push_pin",
            on_click=lambda _, cid=card.id, cur=card.is_template: (
                self._on_toggle_template(cid, not cur)  # type: ignore[misc]
                if self._on_toggle_template
                else None
            ),
        ).props(_ICON_BTN_PROPS).style(pin_opacity).tooltip(
            "Template" if card.is_template else "Make template"
        )

        # Move / Copy menu
        if self._on_move_copy:
            with (
                ui.button(icon="drive_file_move")
                .props(_ICON_BTN_PROPS)
                .style(_ICON_BTN_OPACITY)
                .tooltip("Move / Copy"),
                ui.menu() as mc_menu,
            ):
                ui.menu_item(
                    "Move to…",
                    on_click=lambda _, cid=card.id: (
                        self._on_move_copy(cid, "move"),
                        mc_menu.close(),
                    ),
                )
                ui.menu_item(
                    "Copy to…",
                    on_click=lambda _, cid=card.id: (
                        self._on_move_copy(cid, "copy"),
                        mc_menu.close(),
                    ),
                )

        # Delete button
        ui.button(
            icon="close",
            on_click=lambda _, cid=card.id: (
                self._on_delete(cid)  # type: ignore[misc]
                if self._on_delete
                else None
            ),
        ).props(_ICON_BTN_PROPS).style(_ICON_BTN_OPACITY).tooltip("Delete card")

    def _build_label_picker(self, card: Card, available_labels: list[Label]) -> None:
        """Build the label picker menu."""
        with (
            ui.button(icon="label")
            .props(_ICON_BTN_PROPS)
            .style(_ICON_BTN_OPACITY)
            .tooltip("Set label"),
            ui.menu() as label_menu,
        ):
            for lbl in available_labels:
                ui.menu_item(
                    lbl.name,
                    on_click=lambda _, lid=lbl.id, cid=card.id: (
                        self._on_set_label(cid, lid),  # type: ignore[misc]
                        label_menu.close(),
                    ),
                ).style(f"border-left:4px solid {lbl.color};padding-left:8px;")
            ui.separator()
            ui.menu_item(
                "Remove label",
                on_click=lambda _, cid=card.id: (
                    self._on_set_label(cid, None),  # type: ignore[misc]
                    label_menu.close(),
                ),
            )

    def _handle_dragstart(self) -> None:
        global dragged  # noqa: PLW0603
        dragged = self

    def _handle_dragover(self) -> None:
        global drop_target  # noqa: PLW0603
        drop_target = self


# ColumnComponent


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

        card_count = len(column.cards)

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

                # Card count badge
                ui.badge(str(card_count)).props("color=grey-5 text-color=white")

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
        global dragged, drop_target, dragged_column  # noqa: PLW0603
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

        if dragged is None:
            return

        target_index = len(self.column_data.cards)
        if (
            drop_target is not None
            and drop_target.parent_slot is not None
            and drop_target.parent_slot.parent is self
        ):
            target_index = self.default_slot.children.index(drop_target)

        dragged.move(target_container=self, target_index=target_index)

        if self._on_drop_card:
            self._on_drop_card(
                dragged.card_data.id,  # type: ignore[arg-type]
                self.column_data.id,  # type: ignore[arg-type]
                target_index,
            )

        dragged = None
        drop_target = None

    def _handle_add_card(self, inp: ui.input, column_id: int | None) -> None:
        title = inp.value.strip() if inp.value else ""
        if not title:
            return
        if self._on_add_card and column_id is not None:
            self._on_add_card(column_id, title)
        inp.value = ""
