"""
Add transaction screen.
"""

from datetime import datetime
from typing import Dict, Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.spinner import Spinner
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField


Builder.load_string(
    """
<AddTransactionScreen>:
    name: "add_transaction"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDBoxLayout:
            size_hint_y: None
            height: "48dp"

            MDLabel:
                text: root.title
                font_style: "H6"
                bold: True
                text_size: self.width, None
                shorten: True
                shorten_from: "right"

            MDFlatButton:
                text: "Volver"
                size_hint_x: None
                width: "80dp"
                on_release: root.manager.current = 'transactions'

        MDCard:
            orientation: "vertical"
            size_hint_y: 1
            padding: "12dp"
            spacing: "10dp"

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

                Spinner:
                    id: type_spinner
                    text: root.type_display
                    values: ("gasto", "ingreso", "transferencia")
                    size_hint_y: None
                    height: "40dp"
                    background_normal: ""
                    background_color: app.kivy_palette["primary"]
                    color: (1, 1, 1, 1)
                    on_text: root.on_type_selected(self.text)

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Categoria"
                    size_hint_x: None
                    width: "72dp"
                    theme_text_color: "Hint"

                Spinner:
                    id: category_spinner
                    text: root.category_display
                    values: ()
                    size_hint_y: None
                    height: "40dp"
                    background_normal: ""
                    background_color: app.kivy_palette["primary"]
                    color: (1, 1, 1, 1)
                    on_text: root.on_category_selected(self.text)

            MDBoxLayout:
                size_hint_y: None
                height: "44dp"
                spacing: "8dp"

                MDLabel:
                    text: "Cuenta"
                    size_hint_x: None
                    width: "72dp"
                    theme_text_color: "Hint"

                Spinner:
                    id: account_spinner
                    text: root.account_display
                    values: ()
                    size_hint_y: None
                    height: "40dp"
                    background_normal: ""
                    background_color: app.kivy_palette["primary"]
                    color: (1, 1, 1, 1)
                    on_text: root.on_account_selected(self.text)

            MDTextField:
                id: note
                hint_text: "Nota"
                mode: "rectangle"

            Widget:

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
        self.selected_category_id: Optional[int] = None
        self.selected_account_id: Optional[str] = None
        self.category_id_by_name: Dict[str, int] = {}
        self.account_id_by_name: Dict[str, str] = {}
        self._dialog: Optional[MDDialog] = None

    def on_enter(self, *args):
        self._load_dropdown_data()
        return super().on_enter(*args)

    def _load_dropdown_data(self) -> None:
        if not self.transaction_service:
            return
        session = self.transaction_service.session
        from gf_mobile.persistence.models import Account, Category

        categories = session.query(Category).order_by(Category.name.asc()).all()
        accounts = session.query(Account).order_by(Account.name.asc()).all()

        self.category_id_by_name = {c.name: c.id for c in categories}
        self.account_id_by_name = {a.name: a.id for a in accounts}
        self.ids.category_spinner.values = tuple(self.category_id_by_name.keys())
        self.ids.account_spinner.values = tuple(self.account_id_by_name.keys())

        if categories and self.selected_category_id is None:
            self.selected_category_id = categories[0].id
            self.category_display = categories[0].name
            self.ids.category_spinner.text = self.category_display
        if accounts and self.selected_account_id is None:
            self.selected_account_id = accounts[0].id
            self.account_display = accounts[0].name
            self.ids.account_spinner.text = self.account_display

    def on_type_selected(self, value: str) -> None:
        self.selected_type = value
        self.type_display = value

    def on_category_selected(self, name: str) -> None:
        self.category_display = name
        self.selected_category_id = self.category_id_by_name.get(name)

    def on_account_selected(self, name: str) -> None:
        self.account_display = name
        self.selected_account_id = self.account_id_by_name.get(name)

    def on_save(self) -> None:
        if not self.transaction_service:
            self.status_message = "TransactionService no configurado"
            self._show_popup("Error", self.status_message)
            return

        try:
            amount = float(self.ids.amount.text)
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
                occurred_at=datetime.utcnow(),
            )
            self._trigger_background_sync()
            self.ids.amount.text = ""
            self.ids.note.text = ""
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
        if self._dialog:
            self._dialog.dismiss()
        app = App.get_running_app()
        palette = getattr(app, "kivy_palette", None) if app else None
        if palette:
            button_color = palette["primary"] if title == "Exito" else palette["error"]
        else:
            from gf_mobile.ui.theme import get_kivy_palette

            fallback = get_kivy_palette()
            button_color = fallback["primary"] if title == "Exito" else fallback["error"]
        self._dialog = MDDialog(
            title=title,
            text=message,
            buttons=[
                MDRaisedButton(
                    text="Aceptar",
                    md_bg_color=button_color,
                    on_release=lambda *_: self._dialog.dismiss(),
                )
            ],
        )
        self._dialog.open()
