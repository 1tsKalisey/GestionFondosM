"""
Tests para integración de alertas con sincronización (Slice 7)
"""

import pytest
import json
from datetime import datetime
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import (
    Base,
    Account,
    Category,
    Alert,
    generate_uuid,
)
from gf_mobile.sync.merger import MergerService


@pytest.fixture
def temp_db():
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(temp_db):
    SessionLocal = sessionmaker(bind=temp_db)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def setup_data(session):
    category = Category(id=1, name="Groceries", budget_group="Necesidades")
    account = Account(
        id=generate_uuid(),
        user_id=1,
        name="Main",
        type="checking",
        currency="USD",
        opening_balance=0.0,
    )
    session.add_all([category, account])
    session.flush()
    session.commit()
    return {"category_id": category.id, "account_id": account.id}


class TestAlertMerge:
    def test_merge_alert_create_event(self, session, setup_data):
        """Verifica que un evento remoto de alerta se cree localmente."""
        merger = MergerService(session)
        
        alert_id = generate_uuid()
        event = {
            "id": generate_uuid(),
            "entity_type": "alert",
            "operation": "create",
            "entity_id": alert_id,
            "user_uid": "test-user",
            "device_id": "device-1",
            "client_timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "id": alert_id,
                "alert_type": "budget_overage",
                "severity": "warning",
                "title": "Budget Alert",
                "message": "Groceries budget 80% used",
                "category_id": setup_data["category_id"],
                "amount": 80.0,
                "is_read": False,
                "is_dismissed": False,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "server_id": "alert-server-123",
            }
        }
        
        merger.apply_event(session, event)
        
        alert = session.query(Alert).filter(Alert.id == alert_id).first()
        assert alert is not None
        assert alert.alert_type == "budget_overage"
        assert alert.severity == "warning"
        assert alert.synced is True
        assert alert.server_id == "alert-server-123"

    def test_merge_alert_update_timestamp_wins(self, session, setup_data):
        """Verifica que el merge usa last-write-wins con timestamps."""
        merger = MergerService(session)
        
        alert_id = generate_uuid()
        old_time = datetime(2026, 1, 1, 10, 0, 0).isoformat()
        new_time = datetime(2026, 1, 1, 12, 0, 0).isoformat()
        
        # Crear alerta local
        old_alert = Alert(
            id=alert_id,
            alert_type="budget_overage",
            severity="warning",
            title="Old Title",
            message="Old message",
            category_id=setup_data["category_id"],
            is_read=False,
            is_dismissed=False,
            created_at=datetime(2026, 1, 1, 10, 0, 0),
            updated_at=datetime(2026, 1, 1, 10, 0, 0),
        )
        session.add(old_alert)
        session.commit()
        
        # Evento remoto más nuevo
        event = {
            "id": generate_uuid(),
            "entity_type": "alert",
            "operation": "update",
            "entity_id": alert_id,
            "user_uid": "test-user",
            "device_id": "device-1",
            "client_timestamp": new_time,
            "payload": {
                "id": alert_id,
                "alert_type": "budget_overage",
                "severity": "critical",  # Cambio
                "title": "New Title",  # Cambio
                "message": "New message",  # Cambio
                "category_id": setup_data["category_id"],
                "is_read": False,
                "is_dismissed": False,
                "updated_at": new_time,  # Timestamp más nuevo
            }
        }
        
        merger.apply_event(session, event)
        
        # Verificar que se aplicó el cambio
        updated_alert = session.query(Alert).filter(Alert.id == alert_id).first()
        assert updated_alert.severity == "critical"
        assert updated_alert.title == "New Title"
        assert updated_alert.message == "New message"

    def test_merge_alert_delete_event(self, session, setup_data):
        """Verifica que un evento de delete elimina la alerta."""
        merger = MergerService(session)
        
        alert_id = generate_uuid()
        alert = Alert(
            id=alert_id,
            alert_type="budget_overage",
            severity="warning",
            title="To Delete",
            message="This will be deleted",
            category_id=setup_data["category_id"],
            is_read=False,
            is_dismissed=False,
            created_at=datetime.utcnow(),
        )
        session.add(alert)
        session.commit()
        
        # Evento de delete
        event = {
            "id": generate_uuid(),
            "entity_type": "alert",
            "operation": "delete",
            "entity_id": alert_id,
            "user_uid": "test-user",
            "device_id": "device-1",
            "client_timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "id": alert_id,
            }
        }
        
        merger.apply_event(session, event)
        
        deleted_alert = session.query(Alert).filter(Alert.id == alert_id).first()
        assert deleted_alert is None
