"""Board page - main NiceGUI page rendering the Kanban board."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from src.ui import dialogs
from src.ui.components import ColumnComponent

if TYPE_CHECKING:
    from src.models import Board, Label
    from src.services.board_service import BoardService
    from src.services.export_service import ExportService


def _init_polyfill() -> str:
    """Return touch-drag polyfill script tag."""
    lines = [
        "(function() {",
        "var dragEl=null,lastOver=null;",
        "document.addEventListener('touchstart',function(e){",
        "var h=e.target.closest('.cursor-grab');if(!h)return;",
        "var c=h.closest('.nicegui-card,.q-card')||h.closest('[draggable]');",
        "if(!c)return;c.setAttribute('draggable','true');dragEl=c;",
        "c.dispatchEvent(new Event('dragstart',{bubbles:true}));",
        "},{passive:true});",
        "document.addEventListener('touchmove',function(e){",
        "if(!dragEl)return;e.preventDefault();var t=e.touches[0];",
        "var el=document.elementFromPoint(t.clientX,t.clientY);",
        "if(el&&el!==lastOver){lastOver=el;",
        "el.dispatchEvent(new Event('dragover',{bubbles:true,cancelable:true}));}",
        "},{passive:false});",
        "document.addEventListener('touchend',function(e){",
        "if(!dragEl)return;var t=e.changedTouches[0];",
        "var el=document.elementFromPoint(t.clientX,t.clientY);",
        "if(el)el.dispatchEvent(new Event('drop',{bubbles:true}));",
        "dragEl.removeAttribute('draggable');dragEl=null;lastOver=null;",
        "},{passive:true});",
        "})();",
    ]
    return "<scr" + "ipt>" + "\n".join(lines) + "</scr" + "ipt>"


_PAGE_STYLE = (
    "<style>"
    "body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%) !important;"
    "background-attachment:fixed !important;min-height:100vh;}"
    ".nicegui-content{padding:16px 24px !important;}"
    "@media(max-width:600px){"
    ".board-columns{flex-direction:column !important;flex-wrap:nowrap !important;}"
    ".board-columns .board-col{min-width:100% !important;max-width:100% !important;}"
    ".nicegui-content{padding:8px 8px !important;}"
    "}"
    ".card-dark .q-btn,.card-dark .q-icon,"
    ".card-dark .q-field__native,.card-dark .q-checkbox__inner{color:#222 !important}"
    ".card-light .q-btn,.card-light .q-icon,"
    ".card-light .q-field__native,.card-light .q-checkbox__inner{color:#fff !important}"
    "</style>"
)


_BULK_BTN_STYLE = "border-radius:16px;text-transform:none;"


class BoardPageController:
    """Encapsulates board page state and event handlers."""

    def __init__(
        self,
        key: str,
        board_service: BoardService,
        export_service: ExportService,
    ) -> None:
        """Set up controller state."""
        self._key = key
        self._bs = board_service
        self._es = export_service
        self._board: Board | None = None
        self._labels: list[Label] = []
        self._bulk_active = False
        self._bulk_selected: set[int] = set()
        self._container = ui.element("div").classes("w-full")

    # -- lifecycle --

    def load_and_render(self) -> None:
        """Load data and perform initial render."""
        self._reload_data()
        with self._container:
            self._render_board()

    def _refresh(self) -> None:
        self._reload_data()
        self._container.clear()
        with self._container:
            self._render_board()

    def _reload_data(self) -> None:
        board = self._bs.load_board(self._key)
        if board is not None:
            self._board = board
        self._labels = self._bs.get_labels()

    # -- render --

    def _render_board(self) -> None:
        assert self._board is not None
        self._render_heading()
        self._render_bulk_bar()
        self._render_columns()

    def _render_heading(self) -> None:
        with ui.row().classes("items-center gap-3 q-mb-md"):
            ui.label(self._board.name).classes("text-h5").style(
                "font-weight:700;color:white;letter-spacing:-0.5px;"
            )
            ui.button(
                icon="sync",
                on_click=self._refresh,
            ).props("flat dense round").classes("text-white").tooltip(
                "Sync from server"
            )
            with (
                ui.button(icon="more_vert")
                .props("flat dense round")
                .classes("text-white")
                .tooltip("Board actions"),
                ui.menu(),
            ):
                self._render_menu()

    def _render_menu(self) -> None:
        ui.menu_item("Add Column", on_click=self._on_add_column)
        ui.separator()
        ui.menu_item("Bulk Edit Mode", on_click=self._on_toggle_bulk)
        ui.menu_item("Rename Board", on_click=self._on_rename_board)
        others = [b for b in self._bs.get_all_boards() if b.id != self._board.id]
        if others:
            ui.menu_item(
                "Switch Board",
                on_click=lambda: dialogs.pick_board_dialog(
                    others,
                    lambda b: ui.navigate.to(f"/?key={b.key}"),
                ),
            )
        ui.menu_item("New Board", on_click=self._on_new_board)
        ui.separator()
        ui.menu_item("Manage Labels", on_click=self._on_manage_labels)
        ui.separator()
        ui.menu_item("Sort Cards", on_click=self._on_sort_cards)
        ui.menu_item("Export", on_click=self._on_export)
        ui.menu_item("Delete Cards", on_click=self._on_delete_cards)

    def _render_bulk_bar(self) -> None:
        if not self._bulk_active:
            return
        with ui.row().classes("items-center gap-2 q-mb-md flex-wrap"):
            ui.icon("checklist").classes("text-white")
            ui.label("Select cards, then:").classes("text-body2 text-white")
            for lbl in self._labels:
                ui.button(
                    lbl.name,
                    on_click=lambda _, lid=lbl.id: self._on_bulk_label(lid),
                ).style(
                    f"background-color:{lbl.color} !important;"
                    "color:white !important;"
                    f"{_BULK_BTN_STYLE}font-weight:500;"
                )
            if self._labels:
                ui.button(
                    "Remove Label",
                    on_click=lambda: self._on_bulk_label(None),
                ).props("flat outline").style(_BULK_BTN_STYLE)
            ui.separator().props("vertical")
            ui.button(
                "Set Template",
                icon="push_pin",
                on_click=lambda: self._on_bulk_template(is_template=True),
            ).props("outline").style(_BULK_BTN_STYLE)
            ui.button(
                "Unset Template",
                icon="push_pin",
                on_click=lambda: self._on_bulk_template(is_template=False),
            ).props("flat outline").style(_BULK_BTN_STYLE)
            ui.button(
                "Cancel",
                on_click=self._on_toggle_bulk,
            ).props("flat").style("text-transform:none;")

    def _render_columns(self) -> None:
        cbs = {
            "on_toggle_completed": self._on_toggle_completed,
            "on_toggle_template": self._on_toggle_template,
            "on_edit_title": self._on_edit_title,
            "on_delete": self._on_delete_card,
            "on_select": self._on_select_card,
            "on_set_label": self._on_set_card_label,
            "on_move_copy": self._on_move_copy,
            "available_labels": self._labels,
        }
        with (
            ui.row()
            .classes("items-start gap-3 flex-nowrap overflow-x-auto board-columns")
            .style("min-height:400px;padding-bottom:16px;")
        ):
            for col in self._board.columns:
                ColumnComponent(
                    col,
                    labels=self._labels,
                    on_rename=self._on_rename_column,
                    on_add_card=self._on_add_card,
                    on_delete_column=self._on_delete_column,
                    on_drop_card=self._on_drop_card,
                    on_drop_column=self._on_drop_column,
                    card_callbacks=cbs,
                    bulk_mode=self._bulk_active,
                )

    # -- column handlers --

    def _on_add_column(self) -> None:
        self._bs.add_column(self._board.id)
        self._refresh()

    def _on_rename_column(self, column_id: int, name: str) -> None:
        error = self._bs.rename_column(self._board.id, column_id, name)
        if error:
            ui.notify(error, type="warning")
            self._refresh()

    def _on_delete_column(self, column_id: int) -> None:
        dialogs.confirm_dialog(
            "Delete this column and all its cards?",
            lambda: (self._bs.delete_column(column_id), self._refresh()),
        )

    # -- card handlers --

    def _on_add_card(self, column_id: int, title: str) -> None:
        self._bs.add_card(column_id, title)
        self._refresh()
        ui.run_javascript(
            f"""setTimeout(function() {{
                var q = '.add-card-input-col-{column_id} input';
                var el = document.querySelector(q);
                if (el) el.focus();
            }}, 200)"""
        )

    def _on_edit_title(self, card_id: int, title: str) -> None:
        self._bs.edit_card_title(card_id, title)

    def _on_set_card_label(self, card_id: int, label_id: int | None) -> None:
        self._bs.set_card_label(card_id, label_id)
        self._refresh()

    def _on_toggle_completed(self, card_id: int, is_completed: bool) -> None:  # noqa: FBT001
        self._bs.toggle_card_completed(card_id, is_completed=is_completed)
        self._refresh()

    def _on_toggle_template(self, card_id: int, is_template: bool) -> None:  # noqa: FBT001
        self._bs.toggle_card_template(card_id, is_template=is_template)
        self._refresh()

    def _on_delete_card(self, card_id: int) -> None:
        self._bs.delete_card(card_id)
        self._refresh()

    def _on_drop_card(
        self,
        card_id: int,
        target_column_id: int,
        position: int,
    ) -> None:
        self._bs.move_card(card_id, target_column_id, position)
        self._refresh()

    def _on_drop_column(self, src_id: int, tgt_id: int) -> None:
        col_ids = [c.id for c in self._board.columns]
        if src_id in col_ids and tgt_id in col_ids:
            col_ids.remove(src_id)
            col_ids.insert(col_ids.index(tgt_id), src_id)
            self._bs.reorder_columns(col_ids)
            self._refresh()

    def _on_select_card(self, card_id: int, selected: bool) -> None:  # noqa: FBT001
        if selected:
            self._bulk_selected.add(card_id)
        else:
            self._bulk_selected.discard(card_id)

    # -- move / copy --

    def _on_move_copy(self, card_id: int, action: str) -> None:
        source_col_name = self._find_card_column_name(card_id)
        other_boards = [b for b in self._bs.get_all_boards() if b.id != self._board.id]

        # Load full column data for other boards so the dialog can list them
        loaded_boards: list[Board] = []
        for b in other_boards:
            full = self._bs.load_board(b.key)
            if full and full.columns:
                loaded_boards.append(full)

        def on_confirm(col_id: int, act: str) -> None:
            if act == "move":
                self._bs.move_card(card_id, col_id, self._bs.card_count(col_id))
                ui.notify("Card moved", type="positive")
            else:
                self._bs.copy_card(card_id, col_id, self._bs.card_count(col_id))
                ui.notify("Card copied", type="positive")
            self._refresh()

        dialogs.move_copy_dialog(
            action,
            loaded_boards,
            self._board,
            source_col_name,
            on_confirm,
        )

    def _find_card_column_name(self, card_id: int) -> str | None:
        for col in self._board.columns:
            for c in col.cards:
                if c.id == card_id:
                    return col.name
        return None

    # -- bulk handlers --

    def _on_toggle_bulk(self) -> None:
        self._bulk_active = not self._bulk_active
        self._bulk_selected = set()
        self._refresh()

    def _on_bulk_label(self, label_id: int | None) -> None:
        if self._bulk_selected:
            self._bs.bulk_set_label(list(self._bulk_selected), label_id)
            self._bulk_selected = set()
            self._bulk_active = False
            self._refresh()

    def _on_bulk_template(self, *, is_template: bool) -> None:
        if self._bulk_selected:
            self._bs.bulk_set_template(
                list(self._bulk_selected),
                is_template=is_template,
            )
            self._bulk_selected = set()
            self._bulk_active = False
            self._refresh()

    # -- board-level handlers --

    def _on_sort_cards(self) -> None:
        self._bs.sort_cards(self._board.id, self._labels)
        self._refresh()

    def _on_export(self) -> None:
        def on_export(completed_only: bool) -> None:  # noqa: FBT001
            fresh = self._bs.load_board(self._key)
            if fresh:
                md = self._es.export(
                    fresh,
                    self._labels,
                    completed_only=completed_only,
                )
                dialogs.export_dialog(md)

        dialogs.export_scope_dialog(on_export)

    def _on_delete_cards(self) -> None:
        def on_pin(card_id: int) -> None:
            self._bs.toggle_card_template(card_id, is_template=True)
            # Reload board data so the preview reflects the change
            self._reload_data()

        def on_delete(completed_only: bool) -> None:  # noqa: FBT001
            if completed_only:
                self._bs.delete_completed_cards(self._board.id)
            else:
                self._bs.delete_all_cards(self._board.id)
            self._refresh()

        dialogs.delete_cards_dialog(lambda: self._board, on_pin, on_delete)

    def _on_manage_labels(self) -> None:
        """Open label management dialog."""

        def on_create(name: str, color: str) -> None:
            result = self._bs.create_label(name, color)
            if isinstance(result, str):
                ui.notify(result, type="warning")
            else:
                self._refresh()

        def on_update(lid: int, name: str, color: str) -> None:
            error = self._bs.update_label(lid, name, color)
            if error:
                ui.notify(error, type="warning")
            else:
                self._refresh()

        with ui.dialog() as dlg, ui.card().classes("p-4 min-w-[350px]"):
            ui.label("Manage Labels").classes("text-h6")
            for lbl in self._labels:
                with ui.row().classes("items-center w-full gap-2"):
                    ui.html(
                        '<span style="display:inline-block;width:16px;height:16px;'
                        f'border-radius:50%;background:{lbl.color};"></span>'
                    )
                    ui.label(lbl.name).classes("flex-grow")
                    ui.button(
                        icon="edit",
                        on_click=lambda _, lid=lbl.id, lb=lbl: (
                            dlg.close(),
                            dialogs.label_editor_dialog(
                                lb,
                                lambda n, c, _lid=lid: on_update(_lid, n, c),
                            ),
                        ),
                    ).props("flat dense round")
                    ui.button(
                        icon="delete",
                        on_click=lambda _, lid=lbl.id: (
                            self._bs.delete_label(lid),
                            dlg.close(),
                            self._refresh(),
                        ),
                    ).props("flat dense round text-negative")
            ui.separator()
            ui.button(
                "Create New Label",
                icon="add",
                on_click=lambda: (
                    dlg.close(),
                    dialogs.label_editor_dialog(None, on_create),
                ),
            ).classes("w-full")
            ui.button("Close", on_click=dlg.close).props("flat").classes(
                "w-full",
            )
        dlg.open()

    def _on_rename_board(self) -> None:
        def on_save(new_name: str, new_key: str) -> None:
            name = new_name.strip()
            if not name:
                ui.notify("Board name is required", type="warning")
                return
            key_error = self._bs.update_board_key(self._board.id, new_key)
            if key_error:
                ui.notify(key_error, type="warning")
                return
            self._bs.rename_board(self._board.id, name)
            ui.navigate.to(f"/?key={new_key}")

        dialogs.rename_board_dialog(
            self._board.name,
            self._board.key,
            on_save,
            self._bs.validate_board_key,
        )

    def _on_new_board(self) -> None:
        def on_save(name: str, new_key: str) -> None:
            name = name.strip()
            if not name:
                ui.notify("Board name is required", type="warning")
                return
            error = self._bs.create_board(name, new_key)
            if error:
                ui.notify(error, type="warning")
                return
            ui.navigate.to(f"/?key={new_key}")

        dialogs.rename_board_dialog(
            "",
            "",
            on_save,
            self._bs.validate_board_key,
        )


def _render_board_selector(board_service: BoardService) -> None:
    """Show a list of all boards when no key is provided."""
    all_boards = board_service.get_all_boards()

    # if no boards in DB
    if not all_boards:
        ui.label("No boards yet").classes("text-h5 text-white q-pa-lg")
        return
    ui.label("Select Board").classes("text-h5").style(
        "font-weight:700;color:white;letter-spacing:-0.5px;"
    )
    with ui.column().classes("gap-2 q-mt-md"):
        for b in all_boards:
            ui.button(
                b.name,
                on_click=lambda _, bk=b.key: ui.navigate.to(f"/?key={bk}"),
            ).props("flat align=left").classes("text-white").style(
                "text-transform:none;font-size:1.1rem;"
            )


def create_board_page(
    board_service: BoardService,
    export_service: ExportService,
    apple_icon_url: str,
) -> None:
    """Register the NiceGUI board page route."""

    @ui.page("/")
    def board_page(key: str = "") -> None:
        ui.colors(primary="#37474f", secondary="#546e7a", negative="#c62828")
        ui.add_head_html(_init_polyfill())
        ui.add_head_html(_PAGE_STYLE)
        ui.add_head_html(f'<link rel="apple-touch-icon" href="{apple_icon_url}">')

        # no key parameter -> board selection
        if not key:
            _render_board_selector(board_service)
            return

        board = board_service.load_board(key)

        # no board of that key
        if board is None:
            _render_board_selector(board_service)
            return

        ctrl = BoardPageController(key, board_service, export_service)
        ctrl.load_and_render()
