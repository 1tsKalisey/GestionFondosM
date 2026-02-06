"""
AlertService: Gestión de alertas del sistema (presupuesto, transacciones recurrentes, objetivos de ahorro)
"""

import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from gf_mobile.persistence.models import Alert, Budget, Transaction, Category, SyncOutbox, generate_uuid


class AlertService:
    """
    Gestiona alertas del sistema: presupuesto excedido, categorías no clasificadas,
    objetivos de ahorro incumplidos, etc.
    
    Patrón: Valida entrada → crea/actualiza ORM → flush() → enqueue SyncOutbox → commit()
    """

    def __init__(self, session: Session):
        self.session = session

    def create_alert(
        self,
        alert_type: str,  # "budget_overage", "recurring_due", "savings_goal_behind"
        severity: str,  # "info", "warning", "critical"
        title: str,
        message: str,
        category_id: Optional[int] = None,
        transaction_id: Optional[str] = None,
        amount: Optional[float] = None,
    ) -> Alert:
        """Crea una nueva alerta y la encola para sincronización."""
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

    def update_alert(
        self,
        alert_id: str,
        is_read: Optional[bool] = None,
        is_dismissed: Optional[bool] = None,
    ) -> Alert:
        """Actualiza el estado de una alerta."""
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
            self.session.flush()

            self._enqueue_sync(
                alert_id=alert.id,
                operation="update",
                payload=self._serialize_alert(alert),
            )
            self.session.commit()

        return alert

    def delete_alert(self, alert_id: str) -> bool:
        """Marca una alerta como eliminada (soft delete via is_dismissed)."""
        alert = self.session.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return False

        alert.is_dismissed = True
        alert.updated_at = datetime.utcnow()
        self.session.flush()

        self._enqueue_sync(
            alert_id=alert.id,
            operation="update",
            payload=self._serialize_alert(alert),
        )
        self.session.commit()
        return True

    def get_unread_alerts(self, limit: int = 50) -> List[Alert]:
        """Obtiene alertas no leídas, ordenadas por severidad (critical primero)."""
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        alerts = (
            self.session.query(Alert)
            .filter(and_(Alert.is_read == False, Alert.is_dismissed == False))
            .all()
        )
        # Ordenar por severidad
        alerts.sort(key=lambda a: severity_order.get(a.severity, 3))
        return alerts[:limit]

    def get_unread_count(self) -> int:
        """Retorna el número de alertas no leídas y no descartadas."""
        return (
            self.session.query(Alert)
            .filter(and_(Alert.is_read == False, Alert.is_dismissed == False))
            .count()
        )

    def mark_as_read(self, alert_id: str) -> Alert:
        """Marca una alerta como leída."""
        return self.update_alert(alert_id, is_read=True)

    def dismiss_alert(self, alert_id: str) -> Alert:
        """Descarta una alerta (no elimina, solo oculta)."""
        return self.update_alert(alert_id, is_dismissed=True)

    def list_pending_sync(self) -> List[Dict[str, Any]]:
        """Retorna alertas pendientes de sincronización."""
        outbox_items = (
            self.session.query(SyncOutbox)
            .filter(
                and_(
                    SyncOutbox.entity_type == "alert",
                    SyncOutbox.synced == False,
                )
            )
            .all()
        )
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
        """Marca un elemento del outbox como sincronizado."""
        outbox = self.session.query(SyncOutbox).filter(SyncOutbox.id == outbox_id).first()
        if outbox:
            outbox.synced = True
            outbox.sync_error = None
            self.session.commit()

    # ==================== Métodos privados ====================

    def _validate_input(
        self, alert_type: str, severity: str, title: str, message: str
    ) -> None:
        """Valida parámetros de entrada."""
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
        """Serializa una alerta para SyncOutbox."""
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
        """Convert datetime to ISO 8601 format with 'Z' suffix for UTC timestamps."""
        if dt is None:
            return None
        # If dt is naive, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if not already
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        # Return ISO format with 'Z' suffix
        return dt.isoformat().replace('+00:00', 'Z')

    def _enqueue_sync(
        self, alert_id: str, operation: str, payload: Dict[str, Any]
    ) -> None:
        """Encola un cambio de alerta para sincronización."""
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type="alert",
            entity_id=alert_id,
            operation=operation,
            payload=json.dumps(payload),
            synced=False,
            created_at=datetime.utcnow(),
        )
        self.session.add(outbox)
