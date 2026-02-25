"""
Quick entry screen for one-tap income/expense actions.
"""

from datetime import datetime
from typing import Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog


Builder.load_string(
    """
<QuickEntryScreen>:
    name: "quick_entry"

    MDFloatLayout:
        md_bg_color: root.page_bg_color
        MDLabel:
            text: "Acceso rapido"
            font_style: "H6"
            bold: True
            size_hint: None, None
            height: "34dp"
            pos_hint: {"x": 0.04, "top": 0.98}

        MDLabel:
            text: "Registra en un toque"
            theme_text_color: "Hint"
            size_hint: None, None
            height: "24dp"
            pos_hint: {"x": 0.04, "top": 0.93}

        AnchorLayout:
            anchor_x: "center"
            anchor_y: "center"
            size_hint: 1, 1

            MDBoxLayout:
                orientation: "horizontal"
                spacing: "8dp"
                size_hint_x: None
                width: "320dp"
                size_hint_y: None
                height: root.height * 0.4

                AnchorLayout:
                    anchor_y: "center"
                    size_hint_x: None
                    

                    MDRaisedButton:
                        text: "-"
                        md_bg_color: root.error_color
                        size_hint: None, None
                        size: root.height * 0.1,root.height * 0.4
                        on_release: root.adjust_amount(-1)

                AnchorLayout:
                    anchor_y: "center"
                    size_hint_x: 1

                    MDTextField:
                        id: amount_input
                        text: root.amount_text
                        helper_text: "Cantidad"
                        helper_text_mode: "on_focus"                        
                        halign: "center"
                        font_size: "32sp"
                        size_hint: 1, None
                        height: root.height * 0.4
                        on_text: root.on_amount_text(self.text)

                AnchorLayout:
                    anchor_y: "center"
                    size_hint_x: None
                    

                    MDRaisedButton:
                        text: "+"
                        md_bg_color: root.success_color
                        size_hint: None, None
                        size: root.height * 0.1,root.height * 0.4
                        on_release: root.adjust_amount(1)

        MDRaisedButton:
            text: "LISTO"
            md_bg_color: root.primary_color
            theme_text_color: "Custom"
            text_color: root.text_primary_color
            size_hint_x: None
            width: root.height * 0.4
            size_hint_y: None
            height: root.height * 0.1
            pos_hint: {"center_x": 0.5, "y": 0.12}
            on_release: root.submit_amount()

        MDFloatingActionButton:
            icon: "home"
            md_bg_color: root.primary_color
            icon_color: root.text_primary_color
            pos_hint: {"right": 0.98, "y": 0.02}
            on_release: root.manager.current = "dashboard"
    """
)


class QuickEntryScreen(Screen):
    status_message = StringProperty("")
    amount_value = NumericProperty(0.0)
    amount_text = StringProperty("0")
    step_value = NumericProperty(1.0)
    page_bg_color = ListProperty([0.95, 0.97, 1, 1])
    primary_color = ListProperty([0, 0, 0, 1])
    success_color = ListProperty([0, 0, 0, 1])
    error_color = ListProperty([0, 0, 0, 1])
    surface_color = ListProperty([1, 1, 1, 1])
    text_primary_color = ListProperty([0, 0, 0, 1])

    def __init__(self, transaction_service=None, **kwargs):
        super().__init__(**kwargs)
        self.transaction_service = transaction_service
        self._dialog: Optional[MDDialog] = None

    def on_enter(self, *args):
        self._apply_theme_colors()
        self._refresh_step()
        return super().on_enter(*args)

    def on_kv_post(self, base_widget):
        self._apply_theme_colors()
        app = App.get_running_app()
        if app:
            app.bind(kivy_palette=lambda *_: self._apply_theme_colors())
        amount_input = self.ids.get("amount_input")
        if amount_input:
            amount_input.bind(height=self._schedule_center_input, font_size=self._schedule_center_input)
            self._schedule_center_input()

    def _schedule_center_input(self, *args) -> None:
        Clock.schedule_once(self._center_input_text, 0)

    def _center_input_text(self, *args) -> None:
        amount_input = self.ids.get("amount_input")
        if not amount_input:
            return
        if getattr(self, "_padding_updating", False):
            return
        try:
            self._padding_updating = True
            amount_input.padding = [0, (amount_input.height - amount_input.font_size) / 2]
        finally:
            self._padding_updating = False

    def _refresh_step(self) -> None:
        app = App.get_running_app()
        if app and hasattr(app, "get_quick_step_value"):
            self.step_value = float(app.get_quick_step_value())
        if self.amount_text.strip() == "":
            self.amount_text = "0"

    def on_amount_text(self, *args) -> None:
        text = ""
        if len(args) >= 2:
            text = args[1]
        elif len(args) == 1:
            text = args[0]
        try:
            self.amount_value = float(text)
        except (TypeError, ValueError):
            self.amount_value = 0.0

    def adjust_amount(self, delta: float) -> None:
        current = 0.0
        try:
            current = float(self.amount_text)
        except (TypeError, ValueError):
            current = 0.0
        step = float(self.step_value) if float(self.step_value) != 0 else 1.0
        new_value = current + (delta * step)
        if float(new_value).is_integer():
            self.amount_text = str(int(new_value))
        else:
            self.amount_text = str(new_value)

    def submit_amount(self) -> None:
        try:
            value = float(self.amount_text)
        except (TypeError, ValueError):
            value = 0.0
        if value == 0:
            self._show_dialog("Error", "Ingresa un monto distinto de 0", is_error=True)
            return
        if value > 0:
            tx_type = "ingreso"
            amount = value
        else:
            tx_type = "gasto"
            amount = abs(value)
        self._create_quick_transaction(tx_type, amount)

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
        app = App.get_running_app()
        palette = getattr(app, "kivy_palette", None) if app else None
        if palette:
            button_color = palette["error"] if is_error else palette["primary"]
        else:
            from gf_mobile.ui.theme import get_kivy_palette

            fallback = get_kivy_palette()
            button_color = fallback["error"] if is_error else fallback["primary"]
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
        palette = getattr(app, "kivy_palette", None) if app else None
        if not palette:
            from gf_mobile.ui.theme import get_kivy_palette

            palette = get_kivy_palette()
        if palette:
            self.page_bg_color = palette.get("background", self.page_bg_color)
            self.primary_color = palette.get("primary", self.primary_color)
            self.success_color = palette.get("success", self.success_color)
            self.error_color = palette.get("error", self.error_color)
            self.surface_color = palette.get("surface", self.surface_color)
            self.text_primary_color = palette.get("text_primary", self.text_primary_color)
        else:
            is_dark = bool(app and getattr(app.theme_cls, "theme_style", "Light") == "Dark")
            self.page_bg_color = [0.10, 0.11, 0.14, 1] if is_dark else [0.95, 0.97, 1, 1]
