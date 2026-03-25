"""Sync status screen."""

from datetime import datetime
import threading

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.button import MDRaisedButton

from gf_mobile.ui.navigation import NavigationBar
from gf_mobile.ui.widgets.shell import HeroCard, ScreenHeader, SectionCard

Builder.load_string(
    """
<SyncStatusScreen>:
    name: "sync_status"

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
                    eyebrow: "SINCRONIZACION"
                    title: root.title
                    subtitle: "Estado actual de Firestore y del outbox local"
                    muted_color: app.kivy_palette["text_secondary"]

                HeroCard:
                    eyebrow: "Ultima actividad"
                    title: root.last_sync
                    supporting_text: root.pending_changes
                    card_color: app.kivy_palette["primary"] if not root.has_error else app.kivy_palette["error"]
                    title_color: 1, 1, 1, 1
                    eyebrow_color: 1, 1, 1, 0.82

                SectionCard:
                    title: "Control manual"
                    subtitle: root.status_message or "Lanza una sync completa cuando necesites confirmar consistencia."
                    card_color: app.kivy_palette["surface"]
                    title_color: app.kivy_palette["text_primary"]
                    muted_color: app.kivy_palette["text_secondary"]

                    MDRaisedButton:
                        text: "Sincronizar ahora"
                        md_bg_color: app.kivy_palette["primary"]
                        on_release: root.on_sync_now()
                        disabled: root.is_syncing

                    MDFlatButton:
                        text: "Volver al perfil"
                        theme_text_color: "Custom"
                        text_color: app.kivy_palette["primary"]
                        on_release: root.manager.current = "profile"

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
            self.ids.nav_bar.current_screen = "profile"
        self.update_pending_count()

    def on_sync_now(self) -> None:
        if not self.sync_service:
            self.status_message = "Servicio de sync no configurado"
            self.has_error = True
            return

        self.is_syncing = True
        self.status_message = "Sincronizando..."
        self.has_error = False

        def _worker():
            try:
                result = self.sync_service.sync_now_blocking(push_limit=100, pull_limit=50)
                Clock.schedule_once(lambda *_: self._apply_sync_result(result))
            except Exception as exc:
                Clock.schedule_once(lambda *_: self._apply_sync_error(exc))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_sync_result(self, result) -> None:
        if result.success:
            self.status_message = f"Completado: {result.pushed} enviados, {result.pulled} recibidos"
            self.has_error = False
            self.update_last_sync_time()
            self.update_pending_count()
            self._refresh_related_screens()
        else:
            self.status_message = f"Error: {result.error}"
            self.has_error = True
        self.is_syncing = False

    def _apply_sync_error(self, exc: Exception) -> None:
        self.status_message = f"Error: {exc}"
        self.has_error = True
        self.is_syncing = False

    def _refresh_related_screens(self) -> None:
        from kivy.app import App

        app = App.get_running_app()
        if not app:
            return
        if hasattr(app, "refresh_ui_session_state"):
            app.refresh_ui_session_state()
        for screen_name in ("dashboard", "transactions_results", "reports"):
            try:
                screen = app.sm.get_screen(screen_name)
                if hasattr(screen, "refresh"):
                    screen.refresh()
            except Exception:
                continue

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
