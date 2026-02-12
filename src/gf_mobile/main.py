"""
Aplicacion principal de GestionFondosM
Punto de entrada de la aplicacion movil
"""

print("[GF_DEBUG] gf_mobile.main imported")


from kivy.uix.screenmanager import ScreenManager
from kivymd.app import MDApp

from gf_mobile.core.config import get_settings
from gf_mobile.persistence.db import init_database, build_engine, build_session_factory
from gf_mobile.ui.theme import get_theme_manager, set_app_theme
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

# Importar las pantallas
from gf_mobile.ui.screens.login_screen import LoginScreen
from gf_mobile.ui.screens.transactions_screen import TransactionsScreen
from gf_mobile.ui.screens.add_transaction_screen import AddTransactionScreen
from gf_mobile.ui.screens.sync_status_screen import SyncStatusScreen
from gf_mobile.ui.screens.dashboard_screen import DashboardScreen
from gf_mobile.ui.screens.categories_screen import CategoriesScreen
from gf_mobile.ui.screens.budgets_screen import BudgetsScreen
from gf_mobile.ui.screens.reports_screen import ReportsScreen
from gf_mobile.ui.navigation import NavigationBar


class GestionFondosMApp(MDApp):
    """Aplicacion principal de GestionFondosM"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("[GF_DEBUG] GestionFondosMApp.__init__")
        self.config_obj = get_settings()
        self.engine = None
        self.session_factory = None
        self.auth_service = None
        self.theme_manager = get_theme_manager()

    def build(self):
        """Construir la aplicacion"""
        # Configurar tema
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.primary_hue = "500"
        self.theme_cls.theme_style = "Light"

        # Cargar tema guardado
        set_app_theme(self.config_obj.THEME)

        # Crear screen manager
        self.sm = ScreenManager()

        # Agregar pantallas
        self.login_screen = LoginScreen(name='login')
        self.dashboard_screen = DashboardScreen(name='dashboard')
        self.transactions_screen = TransactionsScreen(name='transactions')
        self.add_transaction_screen = AddTransactionScreen(name='add_transaction')
        self.categories_screen = CategoriesScreen(name='categories')
        self.budgets_screen = BudgetsScreen(name='budgets')
        self.reports_screen = ReportsScreen(name='reports')
        self.sync_status_screen = SyncStatusScreen(name='sync_status')

        self.sm.add_widget(self.login_screen)
        self.sm.add_widget(self.dashboard_screen)
        self.sm.add_widget(self.transactions_screen)
        self.sm.add_widget(self.add_transaction_screen)
        self.sm.add_widget(self.categories_screen)
        self.sm.add_widget(self.budgets_screen)
        self.sm.add_widget(self.reports_screen)
        self.sm.add_widget(self.sync_status_screen)

        # Iniciar en login
        self.sm.current = 'login'

        return self.sm

    def on_start(self):
        """Inicializacion al arrancar la app"""
        # Asegurar que existe el directorio de BD
        self.config_obj.ensure_db_dir()

        # Inicializar base de datos
        self.engine = build_engine()
        self.session_factory = build_session_factory(self.engine)
        init_database()

        # Inicializar servicio de autenticacion (sin argumentos)
        self.auth_service = AuthService()
        if hasattr(self, "login_screen"):
            self.login_screen.auth_service = self.auth_service

        # Verificar si hay sesión válida (3 meses)
        from gf_mobile.core.session_manager import SessionManager
        session_manager = SessionManager()
        self.session_manager = session_manager
        
        if session_manager.has_valid_session():
            # Si hay sesión válida, ir directamente a transacciones
            session_info = session_manager.get_session_info()
            print(f"✓ Sesión válida encontrada para: {session_info['user_id']}")
            print(f"✓ Días restantes: {session_info['days_remaining']} días")
            self.sm.current = 'dashboard'
            # Ejecutar login success para cargar datos
            self.on_login_success(session_info['user_id'])
        else:
            # Si no hay sesión, mostrar login
            print("ℹ No hay sesión válida. Por favor, inicie sesión.")
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
        print("   - categories")
        print("   - budgets")
        print("   - reports")
        print("   - sync_status")

    def _get_or_create_device_id(self, session) -> str:
        item = session.get(SyncState, "device_id")
        if item and item.value:
            return item.value
        import uuid
        device_id = str(uuid.uuid4())
        session.add(SyncState(key="device_id", value=device_id))
        session.commit()
        return device_id

    def on_login_success(self, user_uid: str) -> None:
        """Callback cuando el login es exitoso"""
        session = self.session_factory()
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
            self.add_transaction_screen.transaction_service = tx_service
            self.dashboard_screen.transaction_service = tx_service
            self.reports_screen.transaction_service = tx_service
            
            # Configurar servicios de categorías
            cat_service = CategoryService(session, user_id=str(local_user.id))
            self.categories_screen.category_service = cat_service
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
            
            # Cambiar a pantalla de dashboard
            self.sm.current = "dashboard"
            
            # Ejecutar sincronización inicial (si es la primera vez) luego incremental
            self._run_initial_and_incremental_sync(user_uid, firestore_client, local_user.id)
        finally:
            session.close()

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
                    print("Iniciando sincronización inicial...")
                    # Ejecutar sincronización inicial de forma sincrónica (es la primera vez)
                    asyncio.run(initial_sync_service.perform_initial_sync())
                    print("✓ Sincronización inicial completada")
                
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
                    Clock.schedule_once(lambda *_: self.transactions_screen.refresh())
                    Clock.schedule_once(lambda *_: self.dashboard_screen.refresh())
            except Exception as e:
                print(f"Error en sincronización: {str(e)}")
        
        threading.Thread(target=_worker, daemon=True).start()

    def on_pause(self):
        """Manejo de pausa de la app"""
        return True

    def on_resume(self):
        """Manejo de reanudacion de la app"""
        pass


def main():
    """Punto de entrada principal"""
    app = GestionFondosMApp()
    try:
        app.run()
    except Exception:
        tb = traceback.format_exc()
        # Intentar escribir el traceback en almacenamiento accesible del dispositivo
        try:
            log_path = os.path.join("/sdcard", "gestionfondosm_crash.log")
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            # Si no se puede escribir en /sdcard, intentar directorio local
            try:
                with open("/tmp/gestionfondosm_crash.log", "w", encoding="utf-8") as f:
                    f.write(tb)
            except Exception:
                pass
        print("Unhandled exception during app startup:\n", tb)


if __name__ == '__main__':
    main()
