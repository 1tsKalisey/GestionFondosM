#!/usr/bin/env python
"""
Script rápido para verificar el estado de la sincronización

Muestra:
- Cambios pendientes en SyncOutbox
- Última sincronización
- Errores recientes
"""

from gf_mobile.persistence.db import build_session_factory, build_engine
from gf_mobile.persistence.models import SyncOutbox, SyncState


def check_sync_status():
    """Verifica el estado de sincronización"""
    engine = build_engine()
    session_factory = build_session_factory(engine)
    session = session_factory()

    try:
        print("=" * 60)
        print("  Estado de Sincronización - GestionFondosM")
        print("=" * 60)
        print()

        # Cambios pendientes
        pending = session.query(SyncOutbox).filter(
            SyncOutbox.synced == False
        ).all()

        print(f"📤 Cambios pendientes de enviar: {len(pending)}")
        if pending:
            for item in pending[:5]:  # Mostrar primeros 5
                print(f"   • {item.event_type} - {item.entity_type} ({item.entity_id[:8]}...)")
                if item.sync_error:
                    print(f"     ⚠️  Error: {item.sync_error}")
            if len(pending) > 5:
                print(f"   ... y {len(pending) - 5} más")

        print()

        # Sincronizados
        synced = session.query(SyncOutbox).filter(
            SyncOutbox.synced == True
        ).count()
        print(f"✅ Cambios sincronizados: {synced}")

        print()

        # Última sincronización
        last_applied = session.query(SyncState).filter(
            SyncState.key == "last_applied_at"
        ).first()

        if last_applied and last_applied.value:
            print(f"🕐 Última pull: {last_applied.value}")
        else:
            print("🕐 Última pull: Nunca")

        last_push = session.query(SyncState).filter(
            SyncState.key == "last_push_timestamp"
        ).first()

        if last_push and last_push.value:
            print(f"🕐 Último push: {last_push.value}")
        else:
            print("🕐 Último push: Nunca")

        print()

        # Device ID
        device = session.query(SyncState).filter(
            SyncState.key == "device_id"
        ).first()

        if device and device.value:
            print(f"📱 Device ID: {device.value[:16]}...")

        print()
        print("=" * 60)

        # Errores recientes
        failed = session.query(SyncOutbox).filter(
            SyncOutbox.synced == False,
            SyncOutbox.sync_error != None,
        ).all()

        if failed:
            print()
            print("⚠️  ERRORES RECIENTES:")
            for item in failed[:3]:
                print(f"   • {item.event_type} - {item.sync_error}")

    finally:
        session.close()


if __name__ == "__main__":
    try:
        check_sync_status()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
