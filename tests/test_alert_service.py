"""
Tests para AlertService
"""

import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, Alert, SyncOutbox
from gf_mobile.services.alert_service import AlertService


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


class TestAlertService:
    def test_create_alert(self, session):
        service = AlertService(session)
        alert = service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Budget Alert",
            message="You have exceeded 80% of your groceries budget",
            category_id=1,
        )
        assert alert.id is not None
        assert alert.severity == "warning"
        assert alert.is_read is False

    def test_update_alert_mark_read(self, session):
        service = AlertService(session)
        alert = service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Budget Alert",
            message="Budget exceeded",
        )
        updated = service.mark_as_read(alert.id)
        assert updated.is_read is True

    def test_dismiss_alert(self, session):
        service = AlertService(session)
        alert = service.create_alert(
            alert_type="general",
            severity="info",
            title="Info",
            message="Test",
        )
        dismissed = service.dismiss_alert(alert.id)
        assert dismissed.is_dismissed is True

    def test_get_unread_alerts(self, session):
        service = AlertService(session)
        service.create_alert(
            alert_type="budget_overage",
            severity="critical",
            title="Critical",
            message="Critical alert",
        )
        service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Warning",
            message="Warning alert",
        )
        unread = service.get_unread_alerts()
        assert len(unread) == 2
        # Debe estar ordenado por severidad: critical primero
        assert unread[0].severity == "critical"
        assert unread[1].severity == "warning"

    def test_get_unread_count(self, session):
        service = AlertService(session)
        service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Alert 1",
            message="Message 1",
        )
        service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Alert 2",
            message="Message 2",
        )
        count = service.get_unread_count()
        assert count == 2

    def test_list_pending_sync(self, session):
        service = AlertService(session)
        alert = service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Test",
            message="Test message",
        )
        pending = service.list_pending_sync()
        assert len(pending) == 1
        assert pending[0]["entity_id"] == alert.id
        assert pending[0]["operation"] == "create"

    def test_mark_synced(self, session):
        service = AlertService(session)
        service.create_alert(
            alert_type="budget_overage",
            severity="warning",
            title="Test",
            message="Test message",
        )
        pending = service.list_pending_sync()
        assert len(pending) == 1
        outbox_id = pending[0]["id"]
        service.mark_synced(outbox_id)
        pending_after = service.list_pending_sync()
        assert len(pending_after) == 0

    def test_invalid_alert_type(self, session):
        service = AlertService(session)
        with pytest.raises(ValueError):
            service.create_alert(
                alert_type="invalid_type",
                severity="warning",
                title="Test",
                message="Test",
            )

    def test_invalid_severity(self, session):
        service = AlertService(session)
        with pytest.raises(ValueError):
            service.create_alert(
                alert_type="budget_overage",
                severity="invalid",
                title="Test",
                message="Test",
            )

    def test_empty_title(self, session):
        service = AlertService(session)
        with pytest.raises(ValueError):
            service.create_alert(
                alert_type="budget_overage",
                severity="warning",
                title="",
                message="Test",
            )
