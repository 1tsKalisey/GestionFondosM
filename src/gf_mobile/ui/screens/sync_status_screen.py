"""
SyncStatusScreen
"""

from kivy.lang import Builder
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


Builder.load_string(
    """
<SyncStatusScreen>:
    name: "sync_status"

    MDBoxLayout:
        orientation: "vertical"
        padding: "16dp"
        spacing: "12dp"

        MDLabel:
            text: root.title
            font_style: "H6"
            halign: "center"

        MDLabel:
            text: root.last_sync
            halign: "center"
            theme_text_color: "Hint"
            size_hint_y: None
            height: "24dp"

        MDLabel:
            text: root.pending_changes
            halign: "center"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: "24dp"

        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: "48dp"
            spacing: "8dp"

            MDRaisedButton:
                text: "Sincronizar Ahora"
                on_release: root.on_sync_now()
                disabled: root.is_syncing

        MDLabel:
            text: root.status_message
            halign: "center"
            theme_text_color: "Hint" if not root.has_error else "Error"
            markup: True

        Widget:
    """
)


class SyncStatusScreen(Screen):
    """Pantalla de estado de sincronización."""

    title = StringProperty("Estado de Sincronización")
    last_sync = StringProperty("Última sync: Nunca")
    pending_changes = StringProperty("Cambios pendientes: 0")
    status_message = StringProperty("")
    is_syncing = BooleanProperty(False)
    has_error = BooleanProperty(False)

    def __init__(self, sync_service=None, **kwargs):
        super().__init__(**kwargs)
        self.sync_service = sync_service
        self.session_factory = None

    def on_enter(self):
        """Called when screen is displayed"""
        self.update_pending_count()

    def on_sync_now(self) -> None:
        """Ejecuta sincronización bidireccional"""
        if not self.sync_service:
            self.status_message = "[color=#ff0000]Servicio de sync no configurado[/color]"
            self.has_error = True
            return

        self.is_syncing = True
        self.status_message = "Sincronizando..."
        self.has_error = False

        try:
            import asyncio
            result = asyncio.run(self.sync_service.sync_now(
                push_limit=100,
                pull_limit=50,
            ))

            if result.success:
                self.status_message = (
                    f"[color=#00aa00]✓ Completado:[/color] "
                    f"{result.pushed} enviados, {result.pulled} recibidos"
                )
                self.has_error = False
                self.update_last_sync_time()
                self.update_pending_count()
            else:
                self.status_message = (
                    f"[color=#ff0000]✗ Error:[/color] {result.error}"
                )
                self.has_error = True

        except Exception as exc:
            self.status_message = f"[color=#ff0000]✗ Error:[/color] {exc}"
            self.has_error = True
        finally:
            self.is_syncing = False

    def update_last_sync_time(self) -> None:
        """Actualiza el timestamp de última sincronización"""
        from datetime import datetime
        now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.last_sync = f"Última sync: {now}"

    def update_pending_count(self) -> None:
        """Actualiza el contador de cambios pendientes"""
        if not self.session_factory:
            return

        try:
            from gf_mobile.persistence.models import SyncOutbox
            session = self.session_factory()
            try:
                count = session.query(SyncOutbox).filter(
                    SyncOutbox.synced == False
                ).count()
                self.pending_changes = f"Cambios pendientes: {count}"
            finally:
                session.close()
        except Exception:
            pass

    def set_last_sync(self, value: str) -> None:
        """Setter for backward compatibility"""
        self.last_sync = value

