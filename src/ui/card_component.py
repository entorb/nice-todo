"""Draggable card component for the TODO board."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from nicegui import ui

from src.ui._shared import (
    _COLOR_CARD_BG,
    _COLOR_CARD_COMPLETED_BG,
    _COLOR_TEXT_DARK,
    _EVENT_KEYDOWN_ENTER,
    _ICON_BTN_OPACITY,
    _ICON_BTN_PROPS,
    _OPACITY_COMPLETED_LABELED,
    _OPACITY_COMPLETED_PLAIN,
    PRIO_ICON_SET,
    REPEAT_ICON_SET,
    REPEAT_ICON_UNSET,
    _contrast_color,
    _DragState,
    prio_choices,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Card, Label

_URL_RE = re.compile(r"https?://[^\s<>\"'\]\[{}|\\^`]+")


def _extract_url(text: str) -> str | None:
    """Return first web URL in text, or None."""
    m = _URL_RE.search(text)
    return m.group(0) if m else None


class CardComponent(ui.card):
    """Draggable card with checkbox, title, label picker, and delete button."""

    def __init__(  # noqa: PLR0913
        self,
        card: Card,
        drag_state: _DragState | None = None,
        label: Label | None = None,
        *,
        on_toggle_completed: Callable[[int, bool], None] | None = None,
        on_toggle_repeat: Callable[[int, bool], None] | None = None,
        on_toggle_prio: Callable[[int, bool | None], None] | None = None,
        on_edit_title: Callable[[int, str], None] | None = None,
        on_delete: Callable[[int], None] | None = None,
        on_select: Callable[[int, bool], None] | None = None,
        on_set_label: Callable[[int, int | None], None] | None = None,
        on_move_copy: Callable[[int, str], None] | None = None,
        on_mount: Callable[[int, CardComponent], None] | None = None,
        available_labels: list[Label] | None = None,
        bulk_mode: bool = False,
    ) -> None:
        """Initialize card component."""
        super().__init__()
        self.card_data = card
        self._drag_state = drag_state
        self._label = label
        self._bulk_mode = bulk_mode
        self._available_labels = available_labels or []
        self._checkbox: ui.checkbox | None = None
        self._on_toggle_completed = on_toggle_completed
        self._on_toggle_repeat = on_toggle_repeat
        self._on_toggle_prio = on_toggle_prio
        self._on_edit_title = on_edit_title
        self._on_delete = on_delete
        self._on_select = on_select
        self._on_set_label = on_set_label
        self._on_move_copy = on_move_copy

        style = self._compute_style(card, label)
        text_color = _contrast_color(label.color) if label else _COLOR_TEXT_DARK
        color_class = "card-dark" if text_color == _COLOR_TEXT_DARK else "card-light"

        with self.classes(f"w-full cursor-pointer {color_class}").style(style):
            self._build_content(card, available_labels)

        # Drag events
        self.on("dragstart", self._handle_dragstart)
        self.on("dragend", lambda: self.props(remove="draggable"))
        self.on("dragover.prevent", self._handle_dragover)

        if on_mount:
            on_mount(card.id if card.id is not None else 0, self)

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

    def _apply_completed_instantly(self, *, is_completed: bool) -> None:
        """Update card appearance instantly for optimistic UI."""
        self.card_data.date_completed = (
            datetime.now(tz=UTC).replace(tzinfo=None) if is_completed else None
        )
        # Update checkbox opacity
        if self._checkbox:
            opacity = "" if is_completed else _ICON_BTN_OPACITY
            self._checkbox.style(opacity)
        # Update card style
        new_style = self._compute_style(self.card_data, self._label)
        self.style(new_style)

    def _build_content(self, card: Card, available_labels: list[Label] | None) -> None:
        """Build the card's inner row content."""
        with ui.row().classes("items-center w-full no-wrap gap-1"):
            self._build_drag_handle()
            self._build_checkboxes(card, bulk_mode=self._bulk_mode)
            self._build_title(card)
            self._build_indicator_icons(card)
            self._build_action_buttons(card, available_labels)

    def sync_visuals(self) -> None:
        """Rebuild card inner content and style from current card_data."""
        self.clear()
        new_style = self._compute_style(self.card_data, self._label)
        self.style(new_style)
        with self:
            self._build_content(self.card_data, self._available_labels)

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
            _sel_state = {"on": False}

            def _toggle_select(
                _e: object,
                cid: int | None = card.id,
                state: dict = _sel_state,
            ) -> None:
                state["on"] = not state["on"]
                icon = "check_circle" if state["on"] else "radio_button_unchecked"
                btn.props(f"icon={icon}")  # type: ignore[union-attr]
                if self._on_select:
                    self._on_select(cid, state["on"])  # type: ignore[arg-type]

            btn = (
                ui.button(
                    icon="radio_button_unchecked",
                    on_click=_toggle_select,
                )
                .props(_ICON_BTN_PROPS + " color=blue-grey")
                .classes("min-w-[24px] min-h-[24px]")
            )

        check_opacity = "" if card.is_completed else _ICON_BTN_OPACITY

        def _on_check_change(e: object, cid: int | None = card.id) -> None:
            """Optimistic update: apply UI changes instantly, save async."""
            new_state = e.value  # type: ignore[union-attr]
            # Apply UI changes immediately
            self._apply_completed_instantly(is_completed=new_state)
            # Notify parent (async save only, no full refresh)
            if self._on_toggle_completed:
                self._on_toggle_completed(cid, new_state)  # type: ignore[arg-type]

        self._checkbox = (
            ui.checkbox(
                value=card.is_completed,
                on_change=_on_check_change,
            )
            .classes("min-w-[24px] min-h-[24px]")
            .props("dense color=green")
            .style(check_opacity)
            .tooltip("Toggle completed")
        )

    def _build_title(self, card: Card) -> None:
        """Build the editable title input."""
        self._title_container = ui.row().classes("flex-grow items-center no-wrap gap-0")
        with self._title_container:
            self._render_title_content(card)

    def _render_title_content(self, card: Card) -> None:
        """Render title input and optional URL button."""
        title_style = "font-size:0.9rem;word-wrap:break-word;"
        input_style = "font-size:0.9rem;"
        if card.prio is True:
            input_style += "font-weight:bold;"
        elif card.prio is False:
            input_style += "font-style:italic;"

        title_input = (
            ui.input(value=card.title)
            .classes("flex-grow cursor-text")
            .props(f'dense borderless autogrow input-style="{input_style}"')
            .style(title_style)
        )

        def on_commit(
            _e: object,
            inp: ui.input = title_input,
            cid: int | None = card.id,
        ) -> None:
            if self._on_edit_title and inp.value:
                self._on_edit_title(cid, inp.value)  # type: ignore[arg-type]
            self.card_data.title = inp.value
            self._refresh_title_content()

        title_input.on(_EVENT_KEYDOWN_ENTER, on_commit)
        title_input.on("blur", on_commit)

        url = _extract_url(card.title)
        if url:
            (
                ui.button(
                    icon="open_in_new",
                    on_click=lambda _, u=url: ui.navigate.to(u, new_tab=True),
                )
                .props(_ICON_BTN_PROPS + " color=primary")
                .tooltip(url)
            )

    def _refresh_title_content(self) -> None:
        """Rebuild title content after edit to sync URL button."""
        self._title_container.clear()
        with self._title_container:
            self._render_title_content(self.card_data)

    def _build_indicator_icons(self, card: Card) -> None:
        """Build clickable indicator icons for repeat and prio flags."""
        _unset: bool | None = False

        if card.prio is True:
            ui.button(
                icon=PRIO_ICON_SET,
                on_click=lambda _, cid=card.id, n=_unset: (
                    self._on_toggle_prio(cid, n)  # type: ignore[misc]
                    if self._on_toggle_prio
                    else None
                ),
            ).props(f"{_ICON_BTN_PROPS} color=red").tooltip(
                "Important (click to unset)"
            )

        if card.is_repeat:
            ui.button(
                icon=REPEAT_ICON_SET,
                on_click=lambda _, cid=card.id: (
                    self._on_toggle_repeat(  # type: ignore[misc]
                        cid, not card.is_repeat
                    )
                    if self._on_toggle_repeat
                    else None
                ),
            ).props(_ICON_BTN_PROPS).tooltip("Repeat (click to unset)")

    def _build_action_buttons(
        self,
        card: Card,
        available_labels: list[Label] | None,
    ) -> None:
        """Build label picker and a three-dot context menu for card actions."""
        label_dialog: ui.dialog | None = None
        if available_labels and self._on_set_label:
            label_dialog = self._build_label_dialog(card, available_labels)
            (
                ui.button(icon="label", on_click=lambda _: label_dialog.open())
                .props(_ICON_BTN_PROPS)
                .style(_ICON_BTN_OPACITY)
                .tooltip("Set label")
            )

        with (
            ui.button(icon="more_vert").props(_ICON_BTN_PROPS).style(_ICON_BTN_OPACITY),
            ui.menu() as ctx_menu,
        ):
            # Repeat toggle
            tpl_icon = REPEAT_ICON_SET
            if card.is_repeat:
                tpl_label = "Unset Repeat"
                tpl_icon = REPEAT_ICON_UNSET
            else:
                tpl_label = "Set Repeat"
            with (
                ui.menu_item(
                    on_click=lambda _, cid=card.id, cur=card.is_repeat: (
                        (
                            self._on_toggle_repeat(cid, not cur),  # type: ignore[misc]
                            ctx_menu.close(),
                        )
                        if self._on_toggle_repeat
                        else None
                    ),
                ),
                ui.row().classes("items-center no-wrap gap-2"),
            ):
                ui.icon(tpl_icon).classes("text-lg")
                ui.label(tpl_label)

            # Prio flag — show all options except current
            for pv, p_icon, p_label in prio_choices(card.prio):
                with (
                    ui.menu_item(
                        on_click=lambda _, cid=card.id, v=pv: (
                            (
                                self._on_toggle_prio(cid, v),  # type: ignore[misc]
                                ctx_menu.close(),
                            )
                            if self._on_toggle_prio
                            else None
                        ),
                    ),
                    ui.row().classes("items-center no-wrap gap-2"),
                ):
                    ui.icon(p_icon).classes("text-lg")
                    ui.label(p_label)

            # Set label (opens dialog)
            if label_dialog:
                ui.separator()
                with (
                    ui.menu_item(
                        on_click=lambda _: (
                            ctx_menu.close(),
                            label_dialog.open(),
                        ),
                    ),
                    ui.row().classes("items-center no-wrap gap-2"),
                ):
                    ui.icon("label").classes("text-lg")
                    ui.label("Set label\u2026")

            ui.separator()

            # Move / Copy
            if self._on_move_copy:
                with (
                    ui.menu_item(
                        on_click=lambda _, cid=card.id: (
                            self._on_move_copy(cid, "move"),
                            ctx_menu.close(),
                        ),
                    ),
                    ui.row().classes("items-center no-wrap gap-2"),
                ):
                    ui.icon("drive_file_move").classes("text-lg")
                    ui.label("Move to…")
                with (
                    ui.menu_item(
                        on_click=lambda _, cid=card.id: (
                            self._on_move_copy(cid, "copy"),
                            ctx_menu.close(),
                        ),
                    ),
                    ui.row().classes("items-center no-wrap gap-2"),
                ):
                    ui.icon("content_copy").classes("text-lg")
                    ui.label("Copy to…")
                ui.separator()

            # Delete
            with (
                ui.menu_item(
                    on_click=lambda _, cid=card.id: (
                        (self._on_delete(cid), ctx_menu.close())  # type: ignore[misc]
                        if self._on_delete
                        else None
                    ),
                ),
                ui.row().classes("items-center no-wrap gap-2"),
            ):
                ui.icon("delete").classes("text-lg text-negative")
                ui.label("Delete").classes("text-negative")

    def _build_label_dialog(
        self, card: Card, available_labels: list[Label]
    ) -> ui.dialog:
        """Build the label select dialog."""
        dialog = ui.dialog()
        with dialog, ui.card().classes("items-stretch gap-1 p-4"):
            for lbl in available_labels:
                ui.button(
                    lbl.name,
                    on_click=lambda _, lid=lbl.id, cid=card.id: (
                        self._on_set_label(cid, lid),  # type: ignore[misc]
                        dialog.close(),
                    ),
                ).style(f"border-left:4px solid {lbl.color};padding-left:8px;")
            ui.separator()
            ui.button(
                "Remove label",
                on_click=lambda _, cid=card.id: (
                    self._on_set_label(cid, None),  # type: ignore[misc]
                    dialog.close(),
                ),
            )
        return dialog

    def _handle_dragstart(self) -> None:
        if self._drag_state is not None:
            self._drag_state.drag_card = self

    def _handle_dragover(self) -> None:
        if self._drag_state is not None:
            self._drag_state.drop_target = self
