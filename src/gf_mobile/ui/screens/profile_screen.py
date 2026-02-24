"""
Profile screen.
"""

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen

from gf_mobile.core.session_manager import SessionManager
from gf_mobile.ui.navigation import NavigationBar


Builder.load_string(
    """
<ProfileScreen>:
    name: "profile"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDLabel:
            text: "Perfil"
            font_style: "H6"
            bold: True
            size_hint_y: None
            height: "36dp"

        MDCard:
            orientation: "vertical"
            adaptive_height: True
            padding: "12dp"
            spacing: "6dp"
            md_bg_color: (0.97, 0.99, 1, 1)

            MDLabel:
                text: "Cuenta"
                bold: True
                font_style: "Body2"

            MDLabel:
                text: root.email_text
                theme_text_color: "Hint"

            MDLabel:
                text: root.session_text
                theme_text_color: "Hint"

        MDCard:
            orientation: "vertical"
            adaptive_height: True
            padding: "12dp"
            spacing: "8dp"

            MDLabel:
                text: "Apariencia"
                bold: True
                font_style: "Body2"

            MDBoxLayout:
                size_hint_y: None
                height: "42dp"
                spacing: "8dp"

                MDRaisedButton:
                    text: "Light"
                    md_bg_color: (0.09, 0.52, 0.66, 1) if root.current_theme == "light" else (0.82, 0.86, 0.90, 1)
                    on_release: root.set_theme("light")

                MDRaisedButton:
                    text: "Dark"
                    md_bg_color: (0.09, 0.52, 0.66, 1) if root.current_theme == "dark" else (0.82, 0.86, 0.90, 1)
                    on_release: root.set_theme("dark")

        MDCard:
            orientation: "vertical"
            adaptive_height: True
            padding: "12dp"
            spacing: "8dp"

            MDLabel:
                text: "Accesos rapidos"
                bold: True
                font_style: "Body2"

            MDTextField:
                id: quick_income_values
                hint_text: "Ingresos (+): ej 5,10,15"
                mode: "rectangle"
                text: root.quick_income_text

            MDTextField:
                id: quick_expense_values
                hint_text: "Gastos (-): ej 5,10,15"
                mode: "rectangle"
                text: root.quick_expense_text

            MDRaisedButton:
                text: "Guardar accesos"
                md_bg_color: (0.09, 0.52, 0.66, 1)
                on_release: root.save_quick_values()

            MDBoxLayout:
                size_hint_y: None
                height: "42dp"
                spacing: "8dp"

                MDLabel:
                    text: "Pantalla rapida al abrir"
                    theme_text_color: "Hint"

                MDSwitch:
                    id: quick_entry_toggle
                    active: root.quick_entry_enabled
                    on_active: root.on_quick_entry_toggle(self.active)

        MDCard:
            orientation: "vertical"
            adaptive_height: True
            padding: "12dp"
            spacing: "8dp"

            MDLabel:
                text: "Opciones"
                bold: True
                font_style: "Body2"

            MDRaisedButton:
                text: "Estado de sincronizacion"
                md_bg_color: (0.09, 0.52, 0.66, 1)
                on_release: root.open_sync_status()

            MDFlatButton:
                text: "Cerrar sesion"
                theme_text_color: "Custom"
                text_color: (0.85, 0.22, 0.20, 1)
                on_release: root.logout()

        MDLabel:
            text: root.status_message
            theme_text_color: "Hint"
            font_style: "Caption"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"
            size_hint_y: None
            height: "24dp"

        Widget:

        NavigationBar:
            id: nav_bar
    """
)


class ProfileScreen(Screen):
    status_message = StringProperty("")
    email_text = StringProperty("Email: -")
    session_text = StringProperty("Sesion: -")
    current_theme = StringProperty("light")
    quick_income_text = StringProperty("5,10,15")
    quick_expense_text = StringProperty("5,10,15")
    quick_entry_enabled = BooleanProperty(True)

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "profile"
        self._refresh_profile_info()
        self._refresh_theme_state()
        self._refresh_quick_values()
        self._refresh_quick_toggle()

    def _refresh_profile_info(self) -> None:
        info = SessionManager().get_session_info()
        if not info:
            self.email_text = "Email: -"
            self.session_text = "Sesion no activa"
            return
        email = info.get("email") or "-"
        days = info.get("days_remaining", 0)
        self.email_text = f"Email: {email}"
        self.session_text = f"Sesion activa ({days} dias restantes)"

    def _refresh_theme_state(self) -> None:
        app = App.get_running_app()
        if app and getattr(app.theme_cls, "theme_style", "Light") == "Dark":
            self.current_theme = "dark"
        else:
            self.current_theme = "light"

    def _refresh_quick_values(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "get_quick_button_values"):
            return
        income, expense = app.get_quick_button_values()
        self.quick_income_text = ",".join(str(int(v) if float(v).is_integer() else v) for v in income)
        self.quick_expense_text = ",".join(str(int(v) if float(v).is_integer() else v) for v in expense)

    def _refresh_quick_toggle(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "is_quick_entry_enabled"):
            self.quick_entry_enabled = True
            return
        self.quick_entry_enabled = bool(app.is_quick_entry_enabled())

    def set_theme(self, theme_name: str) -> None:
        app = App.get_running_app()
        if not app:
            return
        try:
            if hasattr(app, "apply_theme"):
                app.apply_theme(theme_name)
            self.current_theme = theme_name
            self.status_message = "Tema actualizado"
        except Exception as exc:
            self.status_message = f"Error: {exc}"

    def open_sync_status(self) -> None:
        self.manager.current = "sync_status"

    def save_quick_values(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "save_quick_button_values"):
            return
        try:
            income = self._parse_group_values(self.ids.quick_income_values.text)
            expense = self._parse_group_values(self.ids.quick_expense_values.text)
            app.save_quick_button_values(income, expense)
            self.quick_income_text = ",".join(str(int(v) if float(v).is_integer() else v) for v in income)
            self.quick_expense_text = ",".join(str(int(v) if float(v).is_integer() else v) for v in expense)
            self.status_message = "Accesos rapidos guardados"
        except Exception as exc:
            self.status_message = f"Error: {exc}"

    def on_quick_entry_toggle(self, active: bool) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "set_quick_entry_enabled"):
            return
        try:
            app.set_quick_entry_enabled(bool(active))
            self.quick_entry_enabled = bool(active)
            self.status_message = "Preferencia guardada"
        except Exception as exc:
            self.status_message = f"Error: {exc}"

    @staticmethod
    def _parse_group_values(text: str):
        values = [x.strip() for x in (text or "").split(",") if x.strip()]
        if len(values) != 3:
            raise ValueError("Debes indicar exactamente 3 valores")
        result = [float(v) for v in values]
        if any(v <= 0 for v in result):
            raise ValueError("Los valores deben ser positivos")
        return result

    def logout(self) -> None:
        app = App.get_running_app()
        if not app:
            return
        try:
            if hasattr(app, "logout_user"):
                app.logout_user()
            else:
                self.manager.current = "login"
            self.status_message = "Sesion cerrada"
        except Exception as exc:
            self.status_message = f"Error: {exc}"
