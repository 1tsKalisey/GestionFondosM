"""
LoginScreen
"""

from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.boxlayout import MDBoxLayout


Builder.load_string(
    """
<LoginScreen>:
    name: "login"

    MDBoxLayout:
        orientation: "vertical"
        padding: "24dp"
        spacing: "16dp"

        MDLabel:
            text: root.title
            halign: "center"
            font_style: "H5"

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
            text: "Iniciar sesion"
            pos_hint: {"center_x": 0.5}
            on_release: root.on_login()

        MDLabel:
            text: "o"
            halign: "center"
            size_hint_y: 0.3

        MDRaisedButton:
            text: "Iniciar sesion con Google"
            pos_hint: {"center_x": 0.5}
            md_bg_color: 0.26, 0.52, 0.96, 1
            on_release: root.on_google_login()

        MDLabel:
            id: status
            text: root.status_message
            halign: "center"
            theme_text_color: "Error"
    """
)


class LoginScreen(Screen):
    """Pantalla de login."""

    title = StringProperty("GestionFondos")
    email = StringProperty("")
    password = StringProperty("")
    status_message = StringProperty("")

    def __init__(self, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self.auth_service = auth_service

    def on_login(self) -> None:
        """Callback de login."""
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            return
        self.status_message = "Iniciando sesion..."
        try:
            import asyncio
            tokens = asyncio.run(self.auth_service.sign_in(self.email, self.password))
            
            # Crear sesión persistente (3 meses)
            from gf_mobile.core.session_manager import SessionManager
            session_manager = SessionManager()
            session_manager.create_session(tokens.user_id, self.email)
            
            from kivy.app import App
            app = App.get_running_app()
            if app:
                app.on_login_success(tokens.user_id)
            self.status_message = "Sesion iniciada"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"

    def on_google_login(self) -> None:
        """Callback de login con Google."""
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            return
        self.status_message = "Abriendo navegador para autenticacion con Google..."
        try:
            import asyncio
            tokens = asyncio.run(self.auth_service.sign_in_with_google())
            
            # Crear sesión persistente (3 meses)
            from gf_mobile.core.session_manager import SessionManager
            session_manager = SessionManager()
            session_manager.create_session(tokens.user_id, self.email)
            
            from kivy.app import App
            app = App.get_running_app()
            if app:
                app.on_login_success(tokens.user_id)
            self.status_message = "Sesion iniciada con Google"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"

    def set_status(self, message: str) -> None:
        self.status_message = message
