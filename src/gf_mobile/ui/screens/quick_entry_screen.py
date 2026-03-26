"""
Quick entry screen for one-tap income/expense actions.
"""

from datetime import datetime, timezone
from typing import Optional

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog

from gf_mobile.ui.dialogs import build_message_dialog
from gf_mobile.ui.screen_utils import apply_palette_attrs, resolve_palette
from gf_mobile.ui.widgets.shell import ScreenHeader, SectionCard


Builder.load_string(
    """
<QuickAdjustButton>:
    size_hint: None, None
    width: root.button_width
    height: root.button_height
    size_hint_min_x: None
    size_hint_min_y: None
    _min_width: root.button_width
    _min_height: root.button_height
    padding: "0dp", "0dp", "0dp", "0dp"

<QuickEntryScreen>:
    name: "quick_entry"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"
        md_bg_color: root.page_bg_color

        ScreenHeader:
            eyebrow: "RAPIDO"
            title: "Acceso rapido"
            subtitle: "Captura en un toque sin salir del flujo normal"
            muted_color: app.kivy_palette["text_secondary"]

        SectionCard:
            title: "Importe"
            subtitle: root.status_message or "Usa el paso configurado en perfil para subir o bajar el importe."
            card_color: root.surface_color
            title_color: app.kivy_palette["text_primary"]
            muted_color: app.kivy_palette["text_secondary"]

            MDTextField:
                id: amount_input
                text: root.amount_text
                helper_text: "Cantidad"
                helper_text_mode: "on_focus"
                halign: "center"
                font_size: "18sp"
                size_hint_y: None
                height: "48dp"
                on_text: root.on_amount_text(self.text)

        SectionCard:
            title: "Ajuste"
            subtitle: "Sube o baja el importe antes de registrar"
            card_color: root.surface_color
            title_color: app.kivy_palette["text_primary"]
            muted_color: app.kivy_palette["text_secondary"]

            MDBoxLayout:
                adaptive_height: True
                spacing: "10dp"

                QuickAdjustButton:
                    text: "-"
                    md_bg_color: root.error_color
                    font_size: "22sp"
                    on_release: root.adjust_amount(-1)

                QuickAdjustButton:
                    text: "+"
                    md_bg_color: root.success_color
                    font_size: "22sp"
                    on_release: root.adjust_amount(1)

            MDBoxLayout:
                adaptive_height: True
                spacing: "8dp"

                MDRaisedButton:
                    text: "Guardar rapido"
                    md_bg_color: root.primary_color
                    theme_text_color: "Custom"
                    text_color: root.text_primary_color
                    size_hint_x: 1
                    on_release: root.submit_amount()

                MDFlatButton:
                    text: "Dashboard"
                    theme_text_color: "Custom"
                    text_color: root.primary_color
                    on_release: root.manager.current = "dashboard"

        Widget:
    """
)


class QuickAdjustButton(MDRaisedButton):
    button_width = NumericProperty(160)
    button_height = NumericProperty(160)


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
        self._palette_binding_registered = False
        self._palette_callback = lambda *_: self._apply_theme_colors()

    def on_enter(self, *args):
        self._apply_theme_colors()
        self._refresh_step()
        return super().on_enter(*args)

    def on_kv_post(self, base_widget):
        self._apply_theme_colors()
        app = App.get_running_app()
        if not hasattr(self, "_palette_callback"):
            self._palette_callback = lambda *_: self._apply_theme_colors()
        if app and not getattr(self, "_palette_binding_registered", False):
            app.bind(kivy_palette=self._palette_callback)
            self._palette_binding_registered = True

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
        try:
            app = App.get_running_app()
            if not app or not hasattr(app, "create_transaction_entry"):
                self._show_dialog("Error", "Servicio de transacciones no configurado", is_error=True)
                return

            default_account_id = (
                app.get_quick_entry_default_account_id()
                if app and hasattr(app, "get_quick_entry_default_account_id")
                else ""
            )
            default_category_id = (
                app.get_quick_entry_default_category_id(tx_type)
                if app and hasattr(app, "get_quick_entry_default_category_id")
                else None
            )

            accounts = app.list_accounts_snapshot() if hasattr(app, "list_accounts_snapshot") else []
            categories = app.list_categories_snapshot() if hasattr(app, "list_categories_snapshot") else []

            account = next((item for item in accounts if item.id == default_account_id), None)
            if not account:
                account = accounts[0] if accounts else None

            category = next((item for item in categories if item.id == default_category_id), None)
            if not category:
                category = categories[0] if categories else None
            if not account:
                raise ValueError("No hay cuentas disponibles")
            if not category:
                raise ValueError("No hay categorias disponibles")

            app.create_transaction_entry(
                account_id=account.id,
                type_=tx_type,
                amount=amount,
                category_id=category.id,
                note="Acceso rapido",
                occurred_at=datetime.now(timezone.utc),
            )
            self._refresh_related_screens()
            self.amount_value = 0.0
            self.amount_text = "0"
            self._trigger_background_sync()
            sign = "+" if tx_type == "ingreso" else "-"
            self._show_dialog("Exito", f"Movimiento registrado: {sign}{amount}", is_error=False)
        except Exception as exc:
            self._show_dialog("Error", f"{exc}", is_error=True)

    def _trigger_background_sync(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "schedule_background_sync"):
            return
        app.schedule_background_sync(delay_seconds=2.5)

    def _refresh_related_screens(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "sm"):
            return
        current_screen = app.sm.current
        for screen_name in ("dashboard", "transactions", "transactions_results", "reports"):
            try:
                screen = app.sm.get_screen(screen_name)
                if hasattr(screen, "request_refresh"):
                    screen.request_refresh()
                elif hasattr(screen, "refresh") and current_screen == screen_name:
                    screen.refresh()
            except Exception:
                continue

    def _show_dialog(self, title: str, message: str, is_error: bool) -> None:
        app = App.get_running_app()
        palette = resolve_palette()
        if palette:
            button_color = palette["error"] if is_error else palette["primary"]
        else:
            button_color = self.error_color if is_error else self.primary_color
        self._dialog = build_message_dialog(
            self._dialog,
            title=title,
            message=message,
            button_color=button_color,
        )
        self._dialog.open()

    def _apply_theme_colors(self) -> None:
        app = App.get_running_app()
        palette = apply_palette_attrs(
            self,
            {
                "page_bg_color": "background",
                "primary_color": "primary",
                "success_color": "success",
                "error_color": "error",
                "surface_color": "surface",
                "text_primary_color": "text_primary",
            },
        )
        if palette:
            return
        is_dark = bool(app and getattr(app.theme_cls, "theme_style", "Light") == "Dark")
        self.page_bg_color = [0.10, 0.11, 0.14, 1] if is_dark else [0.95, 0.97, 1, 1]
