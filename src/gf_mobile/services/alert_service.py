"""
AlertService: gestion de alertas del sistema.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from gf_mobile.persistence.models import Alert
from gf_mobile.services.sync_outbox import enqueue_sync_outbox, list_pending_sync_outbox, mark_outbox_synced


class AlertService:
    """
    Gestiona alertas del sistema.

    Patron: valida entrada -> muta ORM -> flush() -> enqueue SyncOutbox -> commit().
    """

    def __init__(self, session: Session):
        self.session = session

    def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        message: str,
        category_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Alert:
        """Crea una nueva alerta y la encola para sincronizacion."""
        try:
            self._validate_input(alert_type, severity, title, message)

            alert = Alert(
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                category_id=category_id,
                transaction_id=transaction_id,
                amount=amount,
                is_read=False,
                is_dismissed=False,
                synced=False,
                created_at=datetime.utcnow(),
            )
            self.session.add(alert)
            self.session.flush()

            self._enqueue_sync(
                alert_id=alert.id,
                operation="create",
                payload=self._serialize_alert(alert),
            )
            self.session.commit()
            return alert
        except Exception:
            self.session.rollback()
            raise

    def update_alert(
        self,
        alert_id: str,
        is_read: Optional[bool] = None,
        is_dismissed: Optional[bool] = None,
    ) -> Alert:
        """Actualiza el estado de una alerta."""
        try:
            alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                raise ValueError(f"Alert {alert_id} not found")

            updated = False
            if is_read is not None:
                alert.is_read = is_read
                updated = True
            if is_dismissed is not None:
                alert.is_dismissed = is_dismissed
                updated = True

            if updated:
                alert.updated_at = datetime.utcnow()
                alert.synced = False
                self.session.flush()
                self._enqueue_sync(
                    alert_id=alert.id,
                    operation="update",
                    payload=self._serialize_alert(alert),
                )
                self.session.commit()

            return alert
        except Exception:
            self.session.rollback()
            raise

    def delete_alert(self, alert_id: str) -> bool:
        """Marca una alerta como eliminada via `is_dismissed`."""
        try:
            alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                return False

            alert.is_dismissed = True
            alert.updated_at = datetime.utcnow()
            alert.synced = False
            self.session.flush()

            self._enqueue_sync(
                alert_id=alert.id,
                operation="update",
                payload=self._serialize_alert(alert),
            )
            self.session.commit()
            return True
        except Exception:
            self.session.rollback()
            raise

    def get_unread_alerts(self, limit: int = 50) -> List[Alert]:
        """Obtiene alertas no leidas, ordenadas por severidad."""
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts = (
            self.session.query(Alert)
            .filter(and_(Alert.is_read == False, Alert.is_dismissed == False))
            .all()
        )
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        return alerts[:limit]

    def get_unread_count(self) -> int:
        """Retorna el numero de alertas no leidas y no descartadas."""
        return (
            self.session.query(Alert)
            .filter(and_(Alert.is_read == False, Alert.is_dismissed == False))
            .count()
        )

    def mark_as_read(self, alert_id: str) -> Alert:
        return self.update_alert(alert_id, is_read=True)

    def dismiss_alert(self, alert_id: str) -> Alert:
        return self.update_alert(alert_id, is_dismissed=True)

    def list_pending_sync(self) -> List[Dict[str, Any]]:
        outbox_items = list_pending_sync_outbox(self.session, "alert")
        return [
            {
                "id": item.id,
                "entity_id": item.entity_id,
                "operation": item.operation,
                "payload": item.payload,
                "sync_error": item.sync_error,
            }
            for item in outbox_items
        ]

    def mark_synced(self, outbox_id: int) -> None:
        if mark_outbox_synced(self.session, outbox_id):
            self.session.commit()

    def _validate_input(self, alert_type: str, severity: str, title: str, message: str) -> None:
        valid_types = {"budget_overage", "recurring_due", "savings_goal_behind", "general"}
        if alert_type not in valid_types:
            raise ValueError(f"Invalid alert_type: {alert_type}")

        valid_severities = {"info", "warning", "critical"}
        if severity not in valid_severities:
            raise ValueError(f"Invalid severity: {severity}")

        if not title or not isinstance(title, str):
            raise ValueError("title must be non-empty string")
        if not message or not isinstance(message, str):
            raise ValueError("message must be non-empty string")

    def _serialize_alert(self, alert: Alert) -> Dict[str, Any]:
        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "category_id": alert.category_id,
            "transaction_id": alert.transaction_id,
            "amount": alert.amount,
            "is_read": alert.is_read,
            "is_dismissed": alert.is_dismissed,
            "created_at": self._format_timestamp(alert.created_at),
            "updated_at": self._format_timestamp(alert.updated_at),
            "server_id": alert.server_id,
        }

    def _format_timestamp(self, dt: datetime | None) -> str | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")

    def _enqueue_sync(self, alert_id: str, operation: str, payload: Dict[str, Any]) -> None:
        enqueue_sync_outbox(
            self.session,
            entity_type="alert",
            operation=operation,
            entity_id=alert_id,
            payload=payload,
        )
