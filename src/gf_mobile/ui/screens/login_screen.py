"""
Login screen.
"""

from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen

from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard


Builder.load_string(
    """
<LoginScreen>:
    name: "login"

    MDBoxLayout:
        orientation: "vertical"
        padding: "20dp"
        spacing: "14dp"
        md_bg_color: app.kivy_palette["background"]

        Widget:
            size_hint_y: 0.05

        ScreenHeader:
            eyebrow: "BIENVENIDA"
            title: "GestionFondos"
            subtitle: "La experiencia movil ya usa la nueva shell visual"
            muted_color: app.kivy_palette["text_secondary"]

        HeroCard:
            eyebrow: "Acceso seguro"
            title: "Entra para activar sync y datos locales"
            supporting_text: "Usa email o Google. La sesion local se reutiliza cuando el token sigue siendo valido."
            card_color: app.kivy_palette["primary"]
            title_color: 1, 1, 1, 1
            eyebrow_color: 1, 1, 1, 0.82

        SectionCard:
            title: "Iniciar sesion"
            subtitle: "Credenciales del mismo proyecto Firebase"
            card_color: app.kivy_palette["surface"]
            title_color: app.kivy_palette["text_primary"]
            muted_color: app.kivy_palette["text_secondary"]

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
                md_bg_color: app.kivy_palette["primary"]
                on_release: root.on_login()

            MDFlatButton:
                text: "Continuar con Google"
                disabled: not root.google_login_available
                on_release: root.on_google_login()

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Custom"
            text_color: app.kivy_palette[root.status_color_name]
            text_size: self.width, None
            height: self.texture_size[1]
            size_hint_y: None
            valign: "top"
            shorten: False

        Widget:
    """
)


class LoginScreen(Screen):
    """Login view."""

    email = StringProperty("")
    password = StringProperty("")
    status_message = StringProperty("")
    status_color_name = StringProperty("error")
    google_login_available = BooleanProperty(True)

    def __init__(self, auth_service=None, **kwargs):
        super().__init__(**kwargs)
        self.auth_service = auth_service

    def on_login(self) -> None:
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            self.status_color_name = "error"
            return
        self.status_message = "Iniciando sesion..."
        self.status_color_name = "text_secondary"
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
            self.status_color_name = "success"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"
            self.status_color_name = "error"

    def on_google_login(self) -> None:
        if not self.auth_service:
            self.status_message = "AuthService no configurado"
            self.status_color_name = "error"
            return
        self.status_message = "Abriendo navegador para Google..."
        self.status_color_name = "text_secondary"
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
            self.status_color_name = "success"
        except Exception as exc:  # noqa: BLE001
            self.status_message = f"Error: {exc}"
            self.status_color_name = "error"

    def set_status(self, message: str) -> None:
        self.status_message = message
        self.status_color_name = "text_secondary"
