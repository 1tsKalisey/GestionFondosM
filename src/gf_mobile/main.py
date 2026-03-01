"""
Aplicacion principal de GestionFondosM
Punto de entrada de la aplicacion movil
"""

import sys
import logging

# Configure minimal logging so messages appear in logcat reliably.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("gf_mobile")

logger.info("[GF_DEBUG] gf_mobile.main imported")

from kivy.uix.screenmanager import ScreenManager
from kivy.properties import DictProperty
from kivymd.app import MDApp

from gf_mobile.core.config import get_settings
from gf_mobile.persistence.db import init_database, build_engine, build_session_factory
import json
from gf_mobile.ui.theme import get_kivy_palette, get_theme_manager, set_app_theme
from gf_mobile.ui.responsive import ResponsiveManager
from gf_mobile.core.auth import AuthService
from gf_mobile.sync.firestore_client import FirestoreClient
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.simple_sync import SimpleSyncService
from gf_mobile.sync.initial_sync import InitialSyncService
from gf_mobile.persistence.models import SyncState
from gf_mobile.services.transaction_service import TransactionService
from gf_mobile.services.category_service import CategoryService
from gf_mobile.services.budget_service import BudgetService
from kivy.clock import Clock
import threading
import asyncio
import traceback
import os
import tempfile

# Importar las pantallas
from gf_mobile.ui.screens.login_screen import LoginScreen
from gf_mobile.ui.screens.transactions_screen import TransactionsScreen
from gf_mobile.ui.screens.transactions_results_screen import TransactionsResultsScreen
from gf_mobile.ui.screens.add_transaction_screen import AddTransactionScreen
from gf_mobile.ui.screens.sync_status_screen import SyncStatusScreen
from gf_mobile.ui.screens.dashboard_screen import DashboardScreen
from gf_mobile.ui.screens.categories_screen import CategoriesScreen
from gf_mobile.ui.screens.budgets_screen import BudgetsScreen
from gf_mobile.ui.screens.reports_screen import ReportsScreen
from gf_mobile.ui.screens.profile_screen import ProfileScreen
from gf_mobile.ui.screens.quick_entry_screen import QuickEntryScreen
from gf_mobile.ui.navigation import NavigationBar


class GestionFondosMApp(MDApp):
    """Aplicacion principal de GestionFondosM"""
    kivy_palette = DictProperty({})

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.info("[GF_DEBUG] GestionFondosMApp.__init__")
        self.config_obj = get_settings()
        self.engine = None
        self.session_factory = None
        self.app_session = None
        self.auth_service = None
        self.theme_manager = get_theme_manager()

    def build(self):
        """Construir la aplicacion"""
        # Configurar tema
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.primary_hue = "600"
        self.theme_cls.accent_palette = "Amber"
        self.theme_cls.theme_style = "Light"

        # Cargar tema guardado
        set_app_theme(self.config_obj.THEME)
        self.apply_theme(self.config_obj.THEME, persist=False)

        # Inicializar base de datos y cargar paleta antes de crear pantallas
        self.config_obj.ensure_db_dir()
        self.engine = build_engine()
        self.session_factory = build_session_factory(self.engine)
        init_database()
        self._load_ui_theme_preference()
        self._apply_custom_palette_for_theme(self.config_obj.THEME)
        self.kivy_palette = get_kivy_palette()

        # Crear screen manager
        self.sm = ScreenManager()

        # Agregar pantallas
        self.login_screen = LoginScreen(name='login')
        self.dashboard_screen = DashboardScreen(name='dashboard')
        self.transactions_screen = TransactionsScreen(name='transactions')
        self.transactions_results_screen = TransactionsResultsScreen(name='transactions_results')
        self.add_transaction_screen = AddTransactionScreen(name='add_transaction')
        self.categories_screen = CategoriesScreen(name='categories')
        self.budgets_screen = BudgetsScreen(name='budgets')
        self.reports_screen = ReportsScreen(name='reports')
        self.sync_status_screen = SyncStatusScreen(name='sync_status')
        self.profile_screen = ProfileScreen(name='profile')
        self.quick_entry_screen = QuickEntryScreen(name='quick_entry')

        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.transactions_screen)
        self.sm.add_widget(self.transactions_results_screen)
        self.sm.add_widget(self.add_transaction_screen)
        self.sm.add_widget(self.categories_screen)
        self.sm.add_widget(self.budgets_screen)
        self.sm.add_widget(self.reports_screen)
        self.sm.add_widget(self.sync_status_screen)
        self.sm.add_widget(self.profile_screen)
        self.sm.add_widget(self.quick_entry_screen)

        # Iniciar en login
        self.sm.current = 'login'

        return self.sm

    def on_start(self):
        """Inicializacion al arrancar la app"""
        # Base de datos y paleta ya inicializadas en build()

        # Inicializar servicio de autenticacion (sin argumentos)
        self.auth_service = AuthService()
        if hasattr(self, "login_screen"):
            self.login_screen.auth_service = self.auth_service

        # Verificar si hay sesión válida (3 meses)
        from gf_mobile.core.session_manager import SessionManager
        session_manager = SessionManager()
        self.session_manager = session_manager
        
        if session_manager.has_valid_session() and self._can_resume_auth_session():
            # Si hay sesion valida y autenticacion renovable, entrar directo.
            session_info = session_manager.get_session_info()
            print(f"[OK] Sesion valida encontrada para: {session_info['user_id']}")
            print(f"[OK] Dias restantes: {session_info['days_remaining']} dias")
            self.on_login_success(session_info['user_id'], just_logged_in=False)
        elif session_manager.has_valid_session():
            # Hay sesion local pero no token valido para sync.
            print("[INFO] Sesion local encontrada pero sin autenticacion activa.")
            print("[INFO] Debes iniciar sesion de nuevo para sincronizar.")
            session_manager.logout()
            self.sm.current = 'login'
        else:
            # Si no hay sesion, mostrar login.
            print("[INFO] No hay sesion valida. Por favor, inicie sesion.")
            self.sm.current = 'login'

        print("GestionFondosM iniciada correctamente")
        print(f"Base de datos: {self.config_obj.DB_PATH}")
        print(f"Tema: {self.config_obj.THEME}")
        print(f"Dispositivo: {ResponsiveManager.get_device_type().value}")
        print("Pantallas disponibles:")
        print("   - login")
        print("   - dashboard")
        print("   - transactions")
        print("   - add_transaction")
        print("   - transactions_results")
        print("   - categories")
        print("   - budgets")
        print("   - reports")
        print("   - sync_status")
        print("   - profile")
        print("   - quick_entry")

    def _can_resume_auth_session(self) -> bool:
        """
        Verifica si hay autenticacion reutilizable.
        Intenta refrescar idToken en segundo plano usando refresh_token.
        """
        if not self.auth_service:
            return False
        if not self.auth_service.tokens:
            return False
        if not self.auth_service.tokens.refresh_token:
            return False
        try:
            asyncio.run(self.auth_service.get_valid_id_token())
            return True
        except Exception as exc:
            print(f"[INFO] No se pudo reanudar autenticacion: {exc}")
            return False

    def _get_or_create_device_id(self, session) -> str:
        item = session.query(SyncState).filter(SyncState.key == "device_id").first()
        if item and item.value:
            return item.value
        import uuid
        device_id = str(uuid.uuid4())
        session.add(SyncState(key="device_id", value=device_id))
        session.commit()
        return device_id

    def _load_ui_theme_preference(self) -> None:
        if not self.session_factory:
            return
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "ui_theme").first()
            if item and item.value in {"light", "dark"}:
                self.apply_theme(item.value, persist=False)
        except Exception as exc:
            print(f"[INFO] No se pudo cargar tema persistido: {exc}")
        finally:
            session.close()

    def _custom_palette_key(self, theme_name: str) -> str:
        normalized = "dark" if str(theme_name).lower() == "dark" else "light"
        return f"custom_palette_{normalized}"

    def _load_custom_palette(self, theme_name: str):
        if not self.session_factory:
            return {}
        session = self.session_factory()
        try:
            key = self._custom_palette_key(theme_name)
            item = session.query(SyncState).filter(SyncState.key == key).first()
            if item and item.value:
                return json.loads(item.value)
            return {}
        except Exception:
            return {}
        finally:
            session.close()

    def _save_custom_palette(self, theme_name: str, overrides: dict) -> None:
        if not self.session_factory:
            return
        session = self.session_factory()
        try:
            key = self._custom_palette_key(theme_name)
            item = session.query(SyncState).filter(SyncState.key == key).first()
            payload = json.dumps(overrides or {})
            if item:
                item.value = payload
            else:
                session.add(SyncState(key=key, value=payload))
            session.commit()
        finally:
            session.close()

    def _clear_custom_palette(self, theme_name: str) -> None:
        if not self.session_factory:
            return
        session = self.session_factory()
        try:
            key = self._custom_palette_key(theme_name)
            item = session.query(SyncState).filter(SyncState.key == key).first()
            if item:
                item.value = ""
                session.commit()
        finally:
            session.close()

    def _apply_custom_palette_for_theme(self, theme_name: str) -> None:
        overrides = self._load_custom_palette(theme_name)
        self.theme_manager.apply_overrides(overrides)
        self.kivy_palette = get_kivy_palette()
        self._refresh_palette_on_screens()

    def get_custom_palette_for_current_theme(self) -> dict:
        return self._load_custom_palette(self.config_obj.THEME)

    def save_custom_palette_for_current_theme(self, overrides: dict) -> None:
        self._save_custom_palette(self.config_obj.THEME, overrides)
        self._apply_custom_palette_for_theme(self.config_obj.THEME)

    def apply_custom_palette_overrides(self, overrides: dict) -> None:
        self.theme_manager.apply_overrides(overrides)
        self.kivy_palette = get_kivy_palette()
        self._refresh_palette_on_screens()

    def reset_custom_palette_for_current_theme(self) -> None:
        self._clear_custom_palette(self.config_obj.THEME)
        self.theme_manager.set_theme(self.config_obj.THEME)
        self.kivy_palette = get_kivy_palette()

    def apply_theme(self, theme_name: str, persist: bool = True) -> None:
        normalized = "dark" if str(theme_name).lower() == "dark" else "light"
        set_app_theme(normalized)
        self.config_obj.THEME = normalized
        self.theme_cls.theme_style = "Dark" if normalized == "dark" else "Light"
        self.kivy_palette = get_kivy_palette()
        self._apply_custom_palette_for_theme(normalized)
        self._refresh_palette_on_screens()

        if not persist or not self.session_factory:
            return
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "ui_theme").first()
            if item:
                item.value = normalized
            else:
                session.add(SyncState(key="ui_theme", value=normalized))
            session.commit()
        except Exception as exc:
            print(f"[INFO] No se pudo guardar tema persistido: {exc}")
        finally:
            session.close()

    def _refresh_palette_on_screens(self) -> None:
        if not hasattr(self, "sm"):
            return
        for screen in getattr(self.sm, "screens", []):
            if hasattr(screen, "_apply_theme_colors"):
                try:
                    screen._apply_theme_colors()
                except Exception:
                    pass

    def get_quick_step_value(self) -> float:
        default_value = 5.0
        if not self.session_factory:
            return default_value
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "quick_step_value").first()
            if item and item.value is not None:
                return float(item.value)
            return default_value
        except Exception:
            return default_value
        finally:
            session.close()

    def is_quick_entry_enabled(self) -> bool:
        if not self.session_factory:
            return True
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "quick_entry_enabled").first()
            if not item or item.value is None:
                return True
            return str(item.value).strip().lower() in {"1", "true", "yes", "on"}
        except Exception:
            return True
        finally:
            session.close()

    def set_quick_entry_enabled(self, enabled: bool) -> None:
        if not self.session_factory:
            return
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "quick_entry_enabled").first()
            value = "true" if enabled else "false"
            if item:
                item.value = value
            else:
                session.add(SyncState(key="quick_entry_enabled", value=value))
            session.commit()
        finally:
            session.close()

    def save_quick_step_value(self, step_value: float) -> None:
        if not self.session_factory:
            return
        session = self.session_factory()
        try:
            item = session.query(SyncState).filter(SyncState.key == "quick_step_value").first()
            value = str(float(step_value))
            if item:
                item.value = value
            else:
                session.add(SyncState(key="quick_step_value", value=value))
            session.commit()
        finally:
            session.close()

    def logout_user(self) -> None:
        try:
            if self.auth_service:
                self.auth_service.sign_out()
        except Exception as exc:
            print(f"[INFO] Error al cerrar sesion auth: {exc}")

        try:
            from gf_mobile.core.session_manager import SessionManager

            SessionManager().logout()
        except Exception as exc:
            print(f"[INFO] Error al cerrar sesion local: {exc}")

        if self.app_session is not None:
            try:
                self.app_session.close()
            except Exception:
                pass
            self.app_session = None

        self.sm.current = "login"

    def on_login_success(self, user_uid: str, just_logged_in: bool = True) -> None:
        """Callback cuando el login es exitoso"""
        # Keep one long-lived session for UI services.
        if self.app_session is not None:
            try:
                self.app_session.close()
            except Exception:
                pass
        session = self.session_factory()
        self.app_session = session
        try:
            from gf_mobile.persistence.models import User, Account, Category
            
            # Buscar o crear usuario local
            local_user = session.query(User).first()
            if not local_user:
                # Crear usuario local por primera vez
                local_user = User(name="Usuario", server_uid=user_uid)
                session.add(local_user)
                session.flush()
                
                # Crear cuenta por defecto
                account = Account(
                    user_id=local_user.id,
                    name="Efectivo",
                    type="efectivo",
                    currency="EUR",
                    opening_balance=0.0,
                )
                # Crear categoría por defecto
                category = Category(name="General", budget_group="Otros")
                session.add_all([account, category])
                session.commit()
                print(f"Usuario local creado: {local_user.name} (ID: {local_user.id})")
            else:
                # Actualizar UID del servidor si cambió
                local_user.server_uid = user_uid
                session.commit()
                print(f"Usuario local actualizado: {local_user.name} (ID: {local_user.id})")
            
            # Configurar servicios de transacciones
            tx_service = TransactionService(session, user_id=str(local_user.id))
            self.transactions_screen.transaction_service = tx_service
            self.transactions_results_screen.transaction_service = tx_service
            self.add_transaction_screen.transaction_service = tx_service
            self.dashboard_screen.transaction_service = tx_service
            self.reports_screen.transaction_service = tx_service
            self.quick_entry_screen.transaction_service = tx_service
            
            # Configurar servicios de categorías
            cat_service = CategoryService(session, user_id=str(local_user.id))
            self.categories_screen.category_service = cat_service
            self.transactions_screen.category_service = cat_service
            self.dashboard_screen.category_service = cat_service
            self.reports_screen.category_service = cat_service
            
            # Configurar servicios de presupuestos
            budget_service = BudgetService(session, user_id=str(local_user.id))
            self.budgets_screen.budget_service = budget_service
            self.budgets_screen.category_service = cat_service
            self.dashboard_screen.budget_service = budget_service
            self.reports_screen.budget_service = budget_service
            
            # Configurar sincronización
            device_id = self._get_or_create_device_id(session)
            firestore_client = FirestoreClient(self.config_obj, self.auth_service)
            sync_protocol = SyncProtocol(
                session_factory=self.session_factory,
                firestore_client=firestore_client,
                device_id=device_id,
                user_uid=user_uid,
            )
            sync_service = SimpleSyncService(sync_protocol)
            self.sync_status_screen.sync_service = sync_service
            self.sync_status_screen.session_factory = self.session_factory
            
            quick_enabled = self.is_quick_entry_enabled()
            if not quick_enabled:
                self.sm.current = "dashboard"
            else:
                # Si acaba de loguearse: dashboard. Si ya tenia sesion activa: quick entry.
                self.sm.current = "dashboard" if just_logged_in else "quick_entry"
            
            # Ejecutar sincronización inicial (si es la primera vez) luego incremental
            self._run_initial_and_incremental_sync(user_uid, firestore_client, local_user.id)
        except Exception:
            try:
                session.close()
            except Exception:
                pass
            self.app_session = None
            raise

    def _run_initial_and_incremental_sync(self, user_uid: str, firestore_client, local_user_id: int) -> None:
        """Ejecuta sincronización inicial (si es necesaria) y luego incremental."""
        def _worker():
            try:
                # Crear servicio de sincronización inicial
                initial_sync_service = InitialSyncService(
                    session_factory=self.session_factory,
                    firestore_client=firestore_client,
                    user_uid=user_uid,
                    user_id=local_user_id,
                )
                
                # Verificar si necesita sincronización inicial
                if initial_sync_service.needs_initial_sync():
                    print("Iniciando sincronizacion inicial...")
                    # Ejecutar sincronización inicial de forma sincrónica (es la primera vez)
                    try:
                        asyncio.run(initial_sync_service.perform_initial_sync())
                        print("[OK] Sincronizacion inicial completada")
                    except Exception as exc:
                        # No bloquear la sincronizacion incremental por errores de snapshot inicial.
                        # Con esto se puede recuperar estado desde eventos remotos.
                        print(f"[WARN] Sync inicial fallo, continuando con incremental: {exc}")
                
                # Luego ejecutar sincronización incremental normal
                if self.sync_status_screen.sync_service:
                    result = self.sync_status_screen.sync_service.sync_now_blocking(
                        push_limit=100,
                        pull_limit=50,
                    )
                    if result.success:
                        Clock.schedule_once(
                            lambda *_: self.sync_status_screen.update_last_sync_time()
                        )
                    Clock.schedule_once(lambda *_: self.transactions_results_screen.refresh())
                    Clock.schedule_once(lambda *_: self.dashboard_screen.refresh())
            except Exception as e:
                print(f"Error en sincronizacion: {str(e)}")
                error_message = f"Error en sincronizacion: {str(e)}"
                Clock.schedule_once(
                    lambda *_: setattr(
                        self.sync_status_screen,
                        "status_message",
                        error_message,
                    )
                )
        
        threading.Thread(target=_worker, daemon=True).start()

    def on_pause(self):
        """Manejo de pausa de la app"""
        return True

    def on_resume(self):
        """Manejo de reanudacion de la app"""
        pass

    def on_stop(self):
        """Liberar recursos persistentes al cerrar la app."""
        if self.app_session is not None:
            try:
                self.app_session.close()
            except Exception:
                pass
            self.app_session = None


def main():
    """Punto de entrada principal"""
    # Fijar tamaño de ventana en PC (simulación reducida Nothing Phone 3a Pro).
    try:
        from kivy.core.window import Window
        if not os.environ.get("ANDROID_ARGUMENT"):
            Window.size = (405, 897)
    except Exception:
        pass
    app = GestionFondosMApp()
    try:
        app.run()
    except Exception:
        tb = traceback.format_exc()
        # Evitar /sdcard raíz en Android 13+ (scoped storage).
        crash_paths = []
        android_argument = os.environ.get("ANDROID_ARGUMENT")
        if android_argument:
            crash_paths.append(os.path.join(android_argument, "gestionfondosm_crash.log"))
        crash_paths.extend(
            [
                "/sdcard/Download/gestionfondosm_crash.log",
                os.path.join(tempfile.gettempdir(), "gestionfondosm_crash.log"),
            ]
        )
        for log_path in crash_paths:
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(tb)
                break
            except Exception:
                continue
        print("Unhandled exception during app startup:\n", tb)


if __name__ == '__main__':
    main()

# Ensure the app starts when this module is imported in the Android/P4A
# runtime: python-for-android sets `ANDROID_ARGUMENT` at process start. If
# the module is imported (not executed as __main__), call `main()` once.
try:
    import os as _os, sys as _sys
    if (
        __name__ != "__main__"
        and _os.environ.get("ANDROID_ARGUMENT")
        and not getattr(_sys, "_gf_app_started", False)
    ):
        _sys._gf_app_started = True
        try:
            main()
        except Exception:
            # Let global excepthook handle logging
            raise
except Exception:
    pass
