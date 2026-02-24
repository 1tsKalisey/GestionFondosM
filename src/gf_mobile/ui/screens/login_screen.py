"""
Login screen.
"""

from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen


Builder.load_string(
    """
<LoginScreen>:
    name: "login"

    MDBoxLayout:
        orientation: "vertical"
        padding: "24dp"
        spacing: "16dp"

        Widget:
            size_hint_y: 0.1

        MDLabel:
            text: "GestionFondos"
            halign: "left"
            font_style: "H4"
            bold: True

        MDLabel:
            text: "Controla gastos y sincroniza en segundos"
            halign: "left"
            theme_text_color: "Hint"
            font_style: "Body2"
            size_hint_y: None
            height: "24dp"

        MDCard:
            orientation: "vertical"
            padding: "16dp"
            spacing: "12dp"
            radius: [16, 16, 16, 16]

            MDTextField:
                id: email
                hint_text: "Email"
                mode: "rectangle"
                text: root.email
                on_text: root.email = self.text

            MDTextField:
                id: password
                hint_text: "Contrasena"
                password: True
                mode: "rectangle"
                text: root.password
                on_text: root.password = self.text

            MDRaisedButton:
                text: "Entrar"
                size_hint_y: None
                height: "46dp"
                on_release: root.on_login()

            MDFlatButton:
                text: "Continuar con Google"
                disabled: not root.google_login_available
                on_release: root.on_google_login()

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Error"
            text_size: self.width, None
            max_lines: 2
            shorten: True
            shorten_from: "right"

        Widget:
    """
)


class LoginScreen(Screen):
    """Login view."""

    email = StringProperty("")
    password = StringProperty("")
    status_message = StringProperty("")
    google_login_available = BooleanProperty(True)

    def __init__(self, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self.auth_service = auth_service

    def on_login(self) -> None:
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            return
        self.status_message = "Iniciando sesion..."
        try:
            import asyncio

            tokens = asyncio.run(self.auth_service.sign_in(self.email, self.password))

            from gf_mobile.core.session_manager import SessionManager

            SessionManager().create_session(tokens.user_id, self.email.strip())

            from kivy.app import App

            app = App.get_running_app()
            if app:
                app.on_login_success(tokens.user_id, just_logged_in=True)
            self.status_message = "Sesion iniciada"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"

    def on_google_login(self) -> None:
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            return
        self.status_message = "Abriendo navegador para Google..."
        try:
            import asyncio

            tokens = asyncio.run(self.auth_service.sign_in_with_google())

            from gf_mobile.core.session_manager import SessionManager

            google_email = self.auth_service.get_current_user_email()
            SessionManager().create_session(tokens.user_id, google_email)

            from kivy.app import App

            app = App.get_running_app()
            if app:
                app.on_login_success(tokens.user_id, just_logged_in=True)
            self.status_message = "Sesion iniciada con Google"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"

    def set_status(self, message: str) -> None:
        self.status_message = message
