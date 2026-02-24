"""Sync status screen."""

from datetime import datetime

from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton

from gf_mobile.ui.navigation import NavigationBar

Builder.load_string(
    """
<SyncStatusScreen>:
    name: "sync_status"

    MDBoxLayout:
        orientation: "vertical"
        padding: "12dp"
        spacing: "8dp"

        MDLabel:
            text: root.title
            font_style: "H6"
            bold: True
            size_hint_y: None
            height: "36dp"

        MDCard:
            orientation: "vertical"
            padding: "12dp"
            spacing: "8dp"
            adaptive_height: True

            MDLabel:
                text: root.last_sync
                theme_text_color: "Hint"

            MDLabel:
                text: root.pending_changes
                theme_text_color: "Hint"

            MDRaisedButton:
                text: "Sincronizar ahora"
                on_release: root.on_sync_now()
                disabled: root.is_syncing

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Error" if root.has_error else "Hint"
            text_size: self.width, None
            max_lines: 3
            shorten: True
            shorten_from: "right"

        Widget:
            size_hint_y: 1

        NavigationBar:
            id: nav_bar
    """
)


class SyncStatusScreen(Screen):
    title = StringProperty("Estado de sincronizacion")
    last_sync = StringProperty("Ultima sync: Nunca")
    pending_changes = StringProperty("Cambios pendientes: 0")
    status_message = StringProperty("")
    is_syncing = BooleanProperty(False)
    has_error = BooleanProperty(False)

    def __init__(self, sync_service=None, **kwargs):
        super().__init__(**kwargs)
        self.sync_service = sync_service
        self.session_factory = None

    def on_enter(self):
        if "nav_bar" in self.ids:
            self.ids.nav_bar.screen_manager = self.manager
            self.ids.nav_bar.current_screen = "sync_status"
        self.update_pending_count()

    def on_sync_now(self) -> None:
        if not self.sync_service:
            self.status_message = "Servicio de sync no configurado"
            self.has_error = True
            return

        self.is_syncing = True
        self.status_message = "Sincronizando..."
        self.has_error = False

        try:
            import asyncio

            result = asyncio.run(self.sync_service.sync_now(push_limit=100, pull_limit=50))
            if result.success:
                self.status_message = f"Completado: {result.pushed} enviados, {result.pulled} recibidos"
                self.has_error = False
                self.update_last_sync_time()
                self.update_pending_count()
            else:
                self.status_message = f"Error: {result.error}"
                self.has_error = True
        except Exception as exc:
            self.status_message = f"Error: {exc}"
            self.has_error = True
        finally:
            self.is_syncing = False

    def update_last_sync_time(self) -> None:
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.last_sync = f"Ultima sync: {now}"

    def update_pending_count(self) -> None:
        if not self.session_factory:
            return
        try:
            from gf_mobile.persistence.models import SyncOutbox

            session = self.session_factory()
            try:
                count = session.query(SyncOutbox).filter(SyncOutbox.synced == False).count()
                self.pending_changes = f"Cambios pendientes: {count}"
            finally:
                session.close()
        except Exception:
            pass

    def set_last_sync(self, value: str) -> None:
        self.last_sync = value
