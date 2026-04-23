"""Dialog components for the TODO board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.models import Board, Label

# Shared style constants
_DIALOG_ACTIONS_CLASSES = "w-full justify-end gap-2 mt-4"
_DIALOG_CARD_CLASSES = "p-4 min-w-[300px]"
_BTN_PRIMARY_PROPS = "color=primary"
_STYLE_NOTE = "text-caption text-grey"


def confirm_dialog(message: str, on_confirm: Callable[[], None]) -> ui.dialog:
    """Show a confirmation dialog with Cancel/Confirm buttons."""
    with ui.dialog() as dialog, ui.card().classes("p-4"):
        ui.label(message).classes("text-body1")
        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Confirm",
                on_click=lambda: (on_confirm(), dialog.close()),
            ).props("color=negative")
    dialog.open()
    return dialog


def label_editor_dialog(
    label: Label | None,
    on_save: Callable[[str, str], None],
) -> ui.dialog:
    """Show a create/edit label dialog with name input and color picker."""
    is_edit = label is not None
    title = "Edit Label" if is_edit else "Create Label"
    initial_name = label.name if is_edit else ""
    initial_color = label.color if is_edit else "#cccccc"

    with ui.dialog() as dialog, ui.card().classes(_DIALOG_CARD_CLASSES):
        ui.label(title).classes("text-h6")
        name_input = ui.input(
            label="Name",
            value=initial_name,
        ).classes("w-full")
        color_input = ui.color_input(
            label="Color",
            value=initial_color,
        ).classes("w-full")
        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save",
                on_click=lambda: _save_label(dialog, name_input, color_input, on_save),
            ).props(_BTN_PRIMARY_PROPS)
    dialog.open()
    return dialog


def _save_label(
    dialog: ui.dialog,
    name_input: ui.input,
    color_input: ui.color_input,
    on_save: Callable[[str, str], None],
) -> None:
    """Validate and save label from the editor dialog."""
    name = (name_input.value or "").strip()
    color = (color_input.value or "#cccccc").lower()
    if not color.startswith("#"):
        color = "#cccccc"
    if not name:
        ui.notify("Label name is required", type="warning")
        return
    on_save(name, color)
    dialog.close()


def export_dialog(content: str, fmt: str = "txt") -> ui.dialog:
    """Show export result: rendered HTML or markdown in a textarea."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[400px]"):
        ui.label("Export").classes("text-h6")
        if fmt == "html":
            ui.html(content).classes("w-full").style(
                "max-height:60vh;overflow:auto;padding:8px;"
            )
        else:
            textarea = (
                ui.textarea(
                    value=content,
                )
                .classes("w-full font-mono")
                .props("readonly autogrow")
            )
        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            if fmt == "html":
                ui.button(
                    "Copy to clipboard",
                    icon="content_copy",
                    on_click=lambda: _copy_html_to_clipboard(content),
                ).props(_BTN_PRIMARY_PROPS)
            else:
                ui.button(
                    "Copy to clipboard",
                    icon="content_copy",
                    on_click=lambda: _copy_to_clipboard(textarea.value or ""),
                ).props(_BTN_PRIMARY_PROPS)
            ui.button("Close", on_click=dialog.close).props("flat")
    dialog.open()
    return dialog


async def _copy_to_clipboard(text: str) -> None:
    """Copy text to clipboard via browser JS."""
    escaped = text.replace("\\", "\\\\").replace("`", "\\`")
    await ui.run_javascript(f"navigator.clipboard.writeText(`{escaped}`)")
    ui.notify("Copied to clipboard", type="positive")


async def _copy_html_to_clipboard(html: str) -> None:
    """Copy HTML as rich text so pasting gives formatted content."""
    escaped = html.replace("\\", "\\\\").replace("`", "\\`")
    js = (
        "const html = `" + escaped + "`;"
        "const blob = new Blob([html], {type: 'text/html'});"
        "const item = new ClipboardItem({'text/html': blob});"
        "navigator.clipboard.write([item]);"
    )
    await ui.run_javascript(js)
    ui.notify("Copied to clipboard", type="positive")


def rename_board_dialog(
    current_name: str,
    current_key: str,
    on_save: Callable[[str, str], None],
    validate_key: Callable[[str], str | None],
) -> ui.dialog:
    """Show a dialog to rename the board and edit its key."""
    with ui.dialog() as dialog, ui.card().classes(_DIALOG_CARD_CLASSES):
        ui.label("Rename Board").classes("text-h6")
        name_input = ui.input(label="Board Name", value=current_name).classes("w-full")
        key_input = ui.input(label="Board Key (optional)", value=current_key).classes(
            "w-full"
        )
        error_label = ui.label("").classes("text-negative text-caption")
        error_label.set_visibility(False)
        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save",
                on_click=lambda: _save_rename_board(
                    dialog, name_input, key_input, error_label, on_save, validate_key
                ),
            ).props(_BTN_PRIMARY_PROPS)
    dialog.open()
    return dialog


def _save_rename_board(  # noqa: PLR0913
    dialog: ui.dialog,
    name_input: ui.input,
    key_input: ui.input,
    error_label: ui.label,
    on_save: Callable[[str, str], None],
    validate_key: Callable[[str], str | None],
) -> None:
    """Validate and save the board name and key."""
    name = (name_input.value or "").strip()
    if not name:
        error_label.text = "Board name is required"
        error_label.set_visibility(True)
        return
    new_key = (key_input.value or "").strip()
    # If key is empty, default to lowercase board name
    if not new_key:
        new_key = name.lower()
        key_input.value = new_key
    error = validate_key(new_key)
    if error:
        error_label.text = error
        error_label.set_visibility(True)
        return
    on_save(name, new_key)
    dialog.close()


def export_scope_dialog(
    on_export: Callable[[bool, str], None],
) -> ui.dialog:
    """Show a dialog to choose export scope and format."""
    with ui.dialog() as dialog, ui.card().classes(_DIALOG_CARD_CLASSES):
        ui.label("Export").classes("text-h6")
        scope = ui.toggle(
            {True: "Completed Only", False: "All Cards"},
            value=True,
        ).classes("w-full")
        fmt = ui.toggle(
            {"txt": "Plain", "markdown": "Markdown", "html": "HTML"},
            value="txt",
        ).classes("w-full")
        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Export",
                on_click=lambda: (dialog.close(), on_export(scope.value, fmt.value)),
            ).props(_BTN_PRIMARY_PROPS)
    dialog.open()
    return dialog


def delete_cards_dialog(
    get_board: Callable[[], Board],
    on_pin: Callable[[int], None],
    on_delete: Callable[[bool], None],
) -> ui.dialog:
    """Show a two-step dialog: pick scope, then confirm with card list."""
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[350px] max-w-[500px]"):
        ui.label("Delete Cards").classes("text-h6")
        scope = ui.toggle(
            {True: "Finished Only", False: "All Cards"},
            value=True,
        ).classes("w-full")
        ui.label("Pinned cards will not be deleted.").classes(_STYLE_NOTE)
        preview = ui.column().classes("w-full gap-1 mt-2")

        def _render_preview() -> None:
            preview.clear()
            completed_only: bool = scope.value
            board = get_board()
            with preview:
                total = 0
                for col in board.columns:
                    victims = [
                        c
                        for c in col.cards
                        if not c.is_template and (not completed_only or c.is_completed)
                    ]
                    if not victims:
                        continue
                    ui.label(col.name).classes("text-subtitle2 text-grey-8 mt-1")
                    for card in victims:
                        total += 1
                        with (
                            ui.row()
                            .classes("items-center w-full no-wrap gap-1")
                            .style(
                                "padding:2px 4px;border-radius:4px;background:#fafafa;"
                            )
                        ):
                            ui.label(card.title).classes("flex-grow text-body2").style(
                                "overflow:hidden;text-overflow:ellipsis;"
                            )
                            ui.button(
                                icon="push_pin",
                                on_click=lambda _, cid=card.id: (
                                    on_pin(cid),
                                    _render_preview(),
                                ),
                            ).props("flat dense round size=xs").tooltip(
                                "Pin as template (exclude)"
                            )
                if total == 0:
                    ui.label("No cards to delete.").classes(_STYLE_NOTE)

        scope.on_value_change(lambda _: _render_preview())
        _render_preview()

        with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Delete",
                on_click=lambda: (dialog.close(), on_delete(scope.value)),
            ).props("color=negative")
    dialog.open()
    return dialog


def move_copy_dialog(
    action: str,
    boards: list[Board],
    current_board: Board,
    source_column_name: str | None,
    on_confirm: Callable[[int, str], None],
) -> ui.dialog:
    """
    Show a dialog to move or copy a card to a board/column.

    *on_confirm(column_id, action)* is called with the chosen column id
    and the action string ("move" or "copy").
    """
    all_boards = [current_board, *boards]
    label = "Move" if action == "move" else "Copy"

    with ui.dialog() as dialog, ui.card().classes(_DIALOG_CARD_CLASSES):
        ui.label(label).classes("text-h6")

        board_select = ui.select(
            options={b.id: b.name for b in all_boards},
            value=current_board.id,
            label="Board",
        ).classes("w-full")

        # Build column options reactively
        col_container = ui.column().classes("w-full gap-0")

        def _render_columns() -> None:
            col_container.clear()
            bid = board_select.value
            target = next((b for b in all_boards if b.id == bid), None)
            if target is None or not target.columns:
                with col_container:
                    ui.label("No columns available").classes(_STYLE_NOTE)
                return
            cols = target.columns
            default_id = cols[0].id
            if source_column_name:
                for c in cols:
                    if c.name == source_column_name:
                        default_id = c.id
                        break
            with col_container:
                col_select = ui.select(
                    options={c.id: c.name for c in cols},
                    value=default_id,
                    label="Column",
                ).classes("w-full")
                with ui.row().classes(_DIALOG_ACTIONS_CLASSES):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    ui.button(
                        action.capitalize(),
                        on_click=lambda: (
                            on_confirm(col_select.value, action),
                            dialog.close(),
                        ),
                    ).props(_BTN_PRIMARY_PROPS)

        board_select.on_value_change(lambda _: _render_columns())
        _render_columns()

    dialog.open()
    return dialog
