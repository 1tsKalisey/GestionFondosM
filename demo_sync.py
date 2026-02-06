"""
Script de demostración de sincronización bidireccional

Este script muestra cómo usar la sincronización programáticamente.
"""

import asyncio
from datetime import datetime

from gf_mobile.core.config import get_settings
from gf_mobile.core.auth import AuthService
from gf_mobile.persistence.db import build_engine, build_session_factory, init_database
from gf_mobile.persistence.models import User, Account, Category, Transaction, SyncState, generate_uuid
from gf_mobile.services.transaction_service import TransactionService
from gf_mobile.sync.firestore_client import FirestoreClient
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.simple_sync import SimpleSyncService


async def demo_sync():
    """Demostración de sincronización bidireccional"""

    print("=" * 60)
    print("  GestionFondosM - Demo de Sincronización")
    print("=" * 60)
    print()

    # 1. Configuración
    print("1. Configurando...")
    config = get_settings()
    engine = build_engine()
    session_factory = build_session_factory(engine)
    init_database()

    # 2. Autenticación (requerida para sincronización)
    print("2. Verificando autenticación...")
    auth_service = AuthService()

    if not auth_service.tokens:
        print("   ⚠️  No hay tokens de autenticación guardados")
        print("   ℹ️  Para usar sincronización, primero inicia sesión en la app")
        return

    print(f"   ✓ Usuario autenticado: {auth_service.tokens.user_id}")

    # 3. Obtener/Crear usuario local y device_id
    print("3. Configurando usuario local...")
    session = session_factory()
    try:
        user = session.query(User).first()
        if not user:
            user = User(
                name="Usuario Demo",
                server_uid=auth_service.tokens.user_id,
            )
            session.add(user)
            session.commit()

        # Device ID
        device_state = session.query(SyncState).filter(SyncState.key == "device_id").first()
        if not device_state:
            import uuid
            device_id = str(uuid.uuid4())
            session.add(SyncState(key="device_id", value=device_id))
            session.commit()
        else:
            device_id = device_state.value

        print(f"   ✓ Usuario: {user.name} (ID: {user.id})")
        print(f"   ✓ Device ID: {device_id[:8]}...")

    finally:
        session.close()

    # 4. Crear algunas transacciones de ejemplo (si no existen)
    print("4. Creando transacciones de ejemplo...")
    session = session_factory()
    try:
        # Verificar si hay cuenta y categoría
        account = session.query(Account).first()
        category = session.query(Category).first()

        if not account or not category:
            print("   ⚠️  Faltan cuenta o categoría, créalas primero en la app")
            return

        # Crear transacción de ejemplo
        tx_service = TransactionService(session, user_id=str(user.id))
        
        existing_count = session.query(Transaction).count()
        if existing_count < 3:
            tx = tx_service.create(
                account_id=account.id,
                type_="gasto",
                amount=25.50,
                category_id=category.id,
                currency="EUR",
                merchant="Demo Sync",
                note="Transacción de prueba de sincronización",
                occurred_at=datetime.now(),
            )
            print(f"   ✓ Transacción creada: {tx.id[:8]}... - €{tx.amount}")
        else:
            print(f"   ℹ️  Ya existen {existing_count} transacciones")

    finally:
        session.close()

    # 5. Configurar sincronización
    print("5. Configurando sincronización...")
    firestore_client = FirestoreClient(config, auth_service)
    sync_protocol = SyncProtocol(
        session_factory=session_factory,
        firestore_client=firestore_client,
        device_id=device_id,
        user_uid=auth_service.tokens.user_id,
    )
    sync_service = SimpleSyncService(sync_protocol)
    print("   ✓ Servicios de sync configurados")

    # 6. Ejecutar sincronización
    print()
    print("6. Ejecutando sincronización...")
    print("   → Push: Enviando cambios locales a Firestore...")
    print("   → Pull: Descargando cambios remotos...")
    print()

    result = await sync_service.sync_now(push_limit=100, pull_limit=50)

    # 7. Mostrar resultados
    print("=" * 60)
    print("  RESULTADOS")
    print("=" * 60)

    if result.success:
        print(f"✓ Sincronización exitosa!")
        print(f"  • Eventos enviados (push):    {result.pushed}")
        print(f"  • Eventos recibidos (pull):   {result.pulled}")
        print()

        # Información adicional
        session = session_factory()
        try:
            from gf_mobile.persistence.models import SyncOutbox
            pending = session.query(SyncOutbox).filter(SyncOutbox.synced == False).count()
            total_txs = session.query(Transaction).count()

            print("Estado actual:")
            print(f"  • Cambios pendientes:         {pending}")
            print(f"  • Total transacciones local:  {total_txs}")

            last_sync = sync_service.get_last_sync_info()
            if last_sync.get("last_pull"):
                print(f"  • Última sincronización:      {last_sync['last_pull']}")

        finally:
            session.close()

    else:
        print(f"✗ Error en sincronización:")
        print(f"  {result.error}")
        print()
        print(f"  Estadísticas parciales:")
        print(f"  • Eventos enviados:           {result.pushed}")
        print(f"  • Eventos recibidos:          {result.pulled}")

    print()
    print("=" * 60)


def main():
    """Punto de entrada"""
    try:
        asyncio.run(demo_sync())
    except KeyboardInterrupt:
        print("\n\nInterrumpido por usuario")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
