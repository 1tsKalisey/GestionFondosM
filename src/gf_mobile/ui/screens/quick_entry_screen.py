"""
Quick entry screen for one-tap income/expense actions.
"""

from datetime import datetime
from typing import List, Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog


Builder.load_string(
    """
<QuickEntryScreen>:
    name: "quick_entry"

    MDFloatLayout:
        md_bg_color: root.page_bg_color

        MDBoxLayout:
            orientation: "vertical"
            padding: "14dp"
            spacing: "10dp"
            size_hint: 1, 1

            MDLabel:
                text: "Acceso rapido"
                font_style: "H6"
                bold: True
                size_hint_y: None
                height: "34dp"

            MDLabel:
                text: "Registra en un toque"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "24dp"

            AnchorLayout:
                anchor_x: "center"
                anchor_y: "center"
                size_hint_y: 1

                MDGridLayout:
                    cols: 1
                    spacing: "8dp"
                    size_hint_x: 0.99
                    size_hint_y: 0.98

                    MDRaisedButton:
                        text: root.income_labels[0]
                        md_bg_color: (0.10, 0.60, 0.30, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_income(0)

                    MDRaisedButton:
                        text: root.income_labels[1]
                        md_bg_color: (0.10, 0.60, 0.30, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_income(1)

                    MDRaisedButton:
                        text: root.income_labels[2]
                        md_bg_color: (0.10, 0.60, 0.30, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_income(2)

                    MDRaisedButton:
                        text: root.expense_labels[0]
                        md_bg_color: (0.86, 0.26, 0.22, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_expense(0)

                    MDRaisedButton:
                        text: root.expense_labels[1]
                        md_bg_color: (0.86, 0.26, 0.22, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_expense(1)

                    MDRaisedButton:
                        text: root.expense_labels[2]
                        md_bg_color: (0.86, 0.26, 0.22, 1)
                        size_hint_x: 1
                        size_hint_y: 1
                        on_release: root.add_quick_expense(2)

        MDFloatingActionButton:
            icon: "home"
            md_bg_color: (0.09, 0.52, 0.66, 1)
            pos_hint: {"right": 0.98, "y": 0.02}
            on_release: root.manager.current = "dashboard"
    """
)


class QuickEntryScreen(Screen):
    status_message = StringProperty("")
    income_values = ListProperty([5.0, 10.0, 15.0])
    expense_values = ListProperty([5.0, 10.0, 15.0])
    income_labels = ListProperty(["+5", "+10", "+15"])
    expense_labels = ListProperty(["-5", "-10", "-15"])
    page_bg_color = ListProperty([0.95, 0.97, 1, 1])

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self._dialog: Optional[MDDialog] = None

    def on_enter(self, *args):
        self._apply_theme_colors()
        self._refresh_amounts()
        return super().on_enter(*args)

    def _refresh_amounts(self) -> None:
        app = App.get_running_app()
        if app and hasattr(app, "get_quick_button_values"):
            income, expense = app.get_quick_button_values()
            self.income_values = income
            self.expense_values = expense
        self.income_labels = [f"+{int(v) if float(v).is_integer() else v}" for v in self.income_values]
        self.expense_labels = [f"-{int(v) if float(v).is_integer() else v}" for v in self.expense_values]

    def add_quick_income(self, idx: int) -> None:
        self._create_quick_transaction("ingreso", float(self.income_values[idx]))

    def add_quick_expense(self, idx: int) -> None:
        self._create_quick_transaction("gasto", float(self.expense_values[idx]))

    def _create_quick_transaction(self, tx_type: str, amount: float) -> None:
        if not self.transaction_service:
            self._show_dialog("Error", "Servicio de transacciones no configurado", is_error=True)
            return
        try:
            session = self.transaction_service.session
            from gf_mobile.persistence.models import Account, Category

            account = session.query(Account).first()
            category = session.query(Category).first()
            if not account:
                raise ValueError("No hay cuentas disponibles")
            if not category:
                raise ValueError("No hay categorias disponibles")

            self.transaction_service.create(
                account_id=account.id,
                type_=tx_type,
                amount=amount,
                category_id=category.id,
                note="Acceso rapido",
                occurred_at=datetime.utcnow(),
            )
            self._trigger_background_sync()
            sign = "+" if tx_type == "ingreso" else "-"
            self._show_dialog("Exito", f"Movimiento registrado: {sign}{amount}", is_error=False)
        except Exception as exc:
            self._show_dialog("Error", f"{exc}", is_error=True)

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
                    f"[SYNC][QUICK] success={result.success} "
                    f"pushed={result.pushed} pulled={result.pulled} error={result.error}"
                )
            except Exception as exc:
                print(f"[SYNC][QUICK] background sync error: {exc}")

        threading.Thread(target=_worker, daemon=True).start()

    def _show_dialog(self, title: str, message: str, is_error: bool) -> None:
        if self._dialog:
            self._dialog.dismiss()
        button_color = (0.84, 0.25, 0.22, 1) if is_error else (0.09, 0.52, 0.66, 1)
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

    def _apply_theme_colors(self) -> None:
        app = App.get_running_app()
        is_dark = bool(app and getattr(app.theme_cls, "theme_style", "Light") == "Dark")
        self.page_bg_color = [0.10, 0.11, 0.14, 1] if is_dark else [0.95, 0.97, 1, 1]
