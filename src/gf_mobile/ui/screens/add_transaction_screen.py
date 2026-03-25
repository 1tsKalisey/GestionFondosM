"""
Add transaction screen.
"""

from datetime import datetime, timezone
from typing import Dict, Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField

from gf_mobile.ui.dialogs import build_message_dialog, build_selection_dialog
from gf_mobile.ui.screen_utils import resolve_palette
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<AddTransactionScreen>:
    name: "add_transaction"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"
        md_bg_color: app.kivy_palette["background"]

        ScreenHeader:
            eyebrow: "CAPTURA"
            title: root.title
            subtitle: "Alta rapida de ingresos, gastos y transferencias"
            muted_color: app.kivy_palette["text_secondary"]

        HeroCard:
            eyebrow: "Flujo corto"
            title: root.type_display.capitalize()
            supporting_text: root.status_message or "Completa importe, tipo, categoria y cuenta."
            card_color: app.kivy_palette["primary"]
            title_color: 1, 1, 1, 1
            eyebrow_color: 1, 1, 1, 0.82

            MDFlatButton:
                text: "Volver"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                on_release: root.manager.current = root.origin_screen

        SectionCard:
            title: "Datos del movimiento"
            subtitle: "Formulario operativo"
            card_color: app.kivy_palette["surface"]
            title_color: app.kivy_palette["text_primary"]
            muted_color: app.kivy_palette["text_secondary"]

            MDTextField:
                id: amount
                hint_text: "Monto"
                input_filter: "float"
                mode: "rectangle"

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Tipo"
                    size_hint_x: None
                    width: "72dp"
                    theme_text_color: "Hint"

                MDRaisedButton:
                    id: type_button
                    text: root.type_display
                    size_hint_x: 1
                    md_bg_color: app.kivy_palette["primary"]
                    on_release: root.open_type_picker()

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Categoria"
                    size_hint_x: None
                    width: "72dp"
                    theme_text_color: "Hint"

                MDRaisedButton:
                    id: category_button
                    text: root.category_display
                    size_hint_x: 1
                    md_bg_color: app.kivy_palette["primary"]
                    on_release: root.open_category_picker()

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Cuenta"
                    size_hint_x: None
                    width: "72dp"
                    theme_text_color: "Hint"

                MDRaisedButton:
                    id: account_button
                    text: root.account_display
                    size_hint_x: 1
                    md_bg_color: app.kivy_palette["primary"]
                    on_release: root.open_account_picker()

            MDTextField:
                id: note
                hint_text: "Nota"
                mode: "rectangle"

            MDRaisedButton:
                text: "Guardar"
                size_hint_y: None
                height: "44dp"
                md_bg_color: app.kivy_palette["primary"]
                on_release: root.on_save()
    """
)


class AddTransactionScreen(Screen):
    title = StringProperty("Nueva transaccion")
    status_message = StringProperty("")
    type_display = StringProperty("gasto")
    category_display = StringProperty("Seleccionar")
    account_display = StringProperty("Seleccionar")

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self.selected_type: str = "gasto"
        self.default_type: str = "gasto"
        self.selected_category_id: Optional[int] = None
        self.selected_account_id: Optional[str] = None
        self.category_id_by_name: Dict[str, int] = {}
        self.account_id_by_name: Dict[str, str] = {}
        self.origin_screen: str = "transactions"
        self._dialog: Optional[MDDialog] = None

    def on_enter(self, *args):
        self._apply_entry_context()
        self._load_dropdown_data()
        return super().on_enter(*args)

    def prepare_for_entry(self, tx_type: str = "gasto", origin_screen: str = "transactions") -> None:
        normalized = str(tx_type or "gasto").strip().lower()
        if normalized not in {"gasto", "ingreso", "transferencia"}:
            normalized = "gasto"
        self.default_type = normalized
        self.origin_screen = origin_screen or "transactions"

    def _apply_entry_context(self) -> None:
        self.selected_type = self.default_type
        self.type_display = self.default_type

    def _load_dropdown_data(self) -> None:
        if not self.transaction_service:
            return
        session = self.transaction_service.session
        from gf_mobile.persistence.models import Account, Category

        categories = session.query(Category).order_by(Category.name.asc()).all()
        accounts = session.query(Account).order_by(Account.name.asc()).all()

        self.category_id_by_name = {c.name: c.id for c in categories}
        self.account_id_by_name = {a.name: a.id for a in accounts}

        if categories and self.selected_category_id is None:
            self.selected_category_id = categories[0].id
            self.category_display = categories[0].name
        if accounts and self.selected_account_id is None:
            self.selected_account_id = accounts[0].id
            self.account_display = accounts[0].name

    def on_type_selected(self, value: str) -> None:
        self.selected_type = value
        self.type_display = value

    def open_type_picker(self) -> None:
        self._open_selection_dialog(
            "Tipo de movimiento",
            ["gasto", "ingreso", "transferencia"],
            self.on_type_selected,
        )

    def on_category_selected(self, name: str) -> None:
        self.category_display = name
        self.selected_category_id = self.category_id_by_name.get(name)

    def open_category_picker(self) -> None:
        self._open_selection_dialog(
            "Categoria",
            list(self.category_id_by_name.keys()),
            self.on_category_selected,
        )

    def on_account_selected(self, name: str) -> None:
        self.account_display = name
        self.selected_account_id = self.account_id_by_name.get(name)

    def open_account_picker(self) -> None:
        self._open_selection_dialog(
            "Cuenta",
            list(self.account_id_by_name.keys()),
            self.on_account_selected,
        )

    def on_save(self) -> None:
        if not self.transaction_service:
            self.status_message = "TransactionService no configurado"
            self._show_popup("Error", self.status_message)
            return

        try:
            amount = float(self.ids.amount.text)
            if amount <= 0:
                raise ValueError("El monto debe ser positivo")
            session = self.transaction_service.session

            category_id = self.selected_category_id
            if not category_id:
                from gf_mobile.persistence.models import Category

                category = session.query(Category).first()
                if not category:
                    raise ValueError("No hay categorias disponibles")
                category_id = category.id

            account_id = self.selected_account_id
            if not account_id:
                from gf_mobile.persistence.models import Account

                account = session.query(Account).first()
                if not account:
                    raise ValueError("No hay cuentas disponibles")
                account_id = account.id

            note = self.ids.note.text.strip() or None

            self.transaction_service.create(
                account_id=account_id,
                type_=self.selected_type,
                amount=amount,
                category_id=category_id,
                note=note,
                occurred_at=datetime.now(timezone.utc),
            )
            self._trigger_background_sync()
            self.ids.amount.text = ""
            self.ids.note.text = ""
            self.status_message = "Transaccion guardada correctamente"
            self._show_popup("Exito", "Transaccion guardada correctamente")
        except Exception as exc:
            self.status_message = f"Error: {exc}"
            self._show_popup("Error", self.status_message)

    def _trigger_background_sync(self) -> None:
        app = App.get_running_app()
        sync_screen = getattr(app, "sync_status_screen", None) if app else None
        sync_service = getattr(sync_screen, "sync_service", None) if sync_screen else None
        if not sync_service:
            return

        import asyncio
        import threading

        def _worker():
            try:
                result = asyncio.run(sync_service.sync_now(push_limit=100, pull_limit=50))
                print(
                    f"[SYNC][ADD] success={result.success} "
                    f"pushed={result.pushed} pulled={result.pulled} error={result.error}"
                )
            except Exception as exc:
                print(f"[SYNC][ADD] background sync error: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _show_popup(self, title: str, message: str) -> None:
        palette = resolve_palette()
        button_color = palette["primary"] if title == "Exito" else palette["error"]
        self._dialog = build_message_dialog(
            self._dialog,
            title=title,
            message=message,
            button_color=button_color,
        )
        self._dialog.open()

    def _open_selection_dialog(self, title: str, options, callback) -> None:
        self._dialog = build_selection_dialog(
            self._dialog,
            title=title,
            options=options,
            on_select=callback,
        )
        self._dialog.open()
