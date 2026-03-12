"""
Profile screen.
"""

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import BooleanProperty, ListProperty, StringProperty
from kivy.uix.screenmanager import Screen

from gf_mobile.core.session_manager import SessionManager
from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.screen_utils import apply_palette_attrs
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<ProfileScreen>:
    name: "profile"

    MDBoxLayout:
        orientation: "vertical"
        spacing: "0dp"
        md_bg_color: app.kivy_palette["background"]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "16dp"
                spacing: "12dp"
                size_hint_y: None
                height: self.minimum_height

                ScreenHeader:
                    eyebrow: "PERSONAL"
                    title: "Perfil"
                    subtitle: "Sesion, apariencia y accesos rapidos"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Cuenta"
                    title: root.email_text
                    supporting_text: root.session_text
                    card_color: root.primary_color
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 0.9, 0.95, 1, 1

                SectionCard:
                    title: "Apariencia"
                    subtitle: "Tema global de la app"
                    card_color: root.surface_color
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDBoxLayout:
                        size_hint_y: None
                        height: "42dp"
                        spacing: "8dp"

                        MDRaisedButton:
                            text: "Light"
                            md_bg_color: root.primary_color if root.current_theme == "light" else root.surface_color
                            on_release: root.set_theme("light")

                        MDRaisedButton:
                            text: "Dark"
                            md_bg_color: root.primary_color if root.current_theme == "dark" else root.surface_color
                            on_release: root.set_theme("dark")

                SectionCard:
                    title: "Accesos rapidos"
                    subtitle: "Atajos para captura repetitiva"
                    card_color: root.surface_color
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDTextField:
                        id: quick_step_value
                        hint_text: "Paso +/-: ej 5"
                        mode: "rectangle"
                        text: root.quick_step_text

                    MDRaisedButton:
                        text: "Guardar paso"
                        md_bg_color: root.primary_color
                        on_release: root.save_quick_step()

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

                SectionCard:
                    title: "Sesion y sync"
                    subtitle: root.status_message
                    card_color: root.surface_color
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDRaisedButton:
                        text: "Estado de sincronizacion"
                        md_bg_color: root.primary_color
                        on_release: root.open_sync_status()

                    MDFlatButton:
                        text: "Cerrar sesion"
                        theme_text_color: "Custom"
                        text_color: root.error_color
                        on_release: root.logout()

        NavigationBar:
            id: nav_bar
    """
)


class ProfileScreen(Screen):
    status_message = StringProperty("")
    email_text = StringProperty("Email: -")
    session_text = StringProperty("Sesion: -")
    current_theme = StringProperty("light")
    quick_step_text = StringProperty("5")
    quick_entry_enabled = BooleanProperty(True)
    primary_color = ListProperty([0, 0, 0, 1])
    surface_color = ListProperty([1, 1, 1, 1])
    error_color = ListProperty([0.8, 0, 0, 1])

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "profile"
        self._apply_theme_colors()
        app = App.get_running_app()
        if app:
            app.bind(kivy_palette=lambda *_: self._apply_theme_colors())
        self._refresh_profile_info()
        self._refresh_theme_state()
        self._refresh_quick_values()
        self._refresh_quick_toggle()

    def on_kv_post(self, base_widget):
        self._apply_theme_colors()

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
        if not app or not hasattr(app, "get_quick_step_value"):
            return
        step = app.get_quick_step_value()
        self.quick_step_text = str(int(step) if float(step).is_integer() else step)

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
            self._apply_theme_colors()
            self.status_message = "Tema actualizado"
        except Exception as exc:
            self.status_message = f"Error: {exc}"

    def _apply_theme_colors(self) -> None:
        apply_palette_attrs(
            self,
            {
                "primary_color": "primary",
                "surface_color": "surface",
                "error_color": "error",
            },
        )

    def open_sync_status(self) -> None:
        self.manager.current = "sync_status"


    def save_quick_step(self) -> None:
        app = App.get_running_app()
        if not app or not hasattr(app, "save_quick_step_value"):
            return
        try:
            step = self._parse_step_value(self.ids.quick_step_value.text)
            app.save_quick_step_value(step)
            self.quick_step_text = str(int(step) if float(step).is_integer() else step)
            self.status_message = "Paso guardado"
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
    def _parse_step_value(text: str) -> float:
        value = str(text or "").strip()
        if value == "":
            raise ValueError("Debes indicar un valor")
        result = float(value)
        if result <= 0:
            raise ValueError("El valor debe ser positivo")
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
