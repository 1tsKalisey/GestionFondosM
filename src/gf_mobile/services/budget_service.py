"""
BudgetService

Gestiona presupuestos y alertas asociadas.
"""

import json
from datetime import datetime
from typing import Optional, Tuple, List

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import ValidationError, DatabaseError
from gf_mobile.persistence.models import Budget, Transaction, Alert, SyncOutbox, Category, generate_uuid


class BudgetInput:
    """Input para crear/actualizar presupuestos."""

    def __init__(self, category_id: int, limit: float, month: str):
        self.category_id = category_id
        self.limit = limit
        self.month = month


class BudgetService:
    """Servicio de presupuestos y alertas por sobreconsumo."""

    def __init__(self, session: Session, user_id: str = None):
        self.session = session
        self.user_id = user_id

    # ==================== CRUD ====================

    def create(self, data: BudgetInput) -> Budget:
        """Crea un nuevo presupuesto (interfaz compatible para pantallas)."""
        return self.create_budget(data.category_id, data.month, data.limit)

    def list_all(self) -> List[Budget]:
        """Lista todos los presupuestos (interfaz compatible para pantallas)."""
        return self.session.query(Budget).all()

    def create_budget(self, category_id: int, month: str, amount: float) -> Budget:
        try:
            self._validate(category_id, month, amount)
            budget = Budget(
                id=generate_uuid(),
                category_id=category_id,
                month=month,
                amount=amount,
                synced=False,
            )
            self.session.add(budget)
            self.session.flush()

            self._enqueue_sync("budget", "create", budget.id, self._serialize_budget(budget))
            self.session.commit()
            return budget
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al crear presupuesto: {str(e)}")

    def update_budget(self, budget_id: str, amount: float) -> Budget:
        try:
            budget = self.session.query(Budget).filter(Budget.id == budget_id).first()
            if not budget:
                raise ValidationError(f"Presupuesto no encontrado: {budget_id}")

            budget.amount = amount
            budget.synced = False
            self.session.flush()

            self._enqueue_sync("budget", "update", budget.id, self._serialize_budget(budget))
            self.session.commit()
            return budget
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al actualizar presupuesto: {str(e)}")

    def delete_budget(self, budget_id: str) -> bool:
        try:
            budget = self.session.query(Budget).filter(Budget.id == budget_id).first()
            if not budget:
                raise ValidationError(f"Presupuesto no encontrado: {budget_id}")

            self._enqueue_sync("budget", "delete", budget.id, {})
            self.session.delete(budget)
            self.session.commit()
            return True
        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al eliminar presupuesto: {str(e)}")

    def get_budget(self, category_id: int, month: str) -> Optional[Budget]:
        return self.session.query(Budget).filter(
            and_(Budget.category_id == category_id, Budget.month == month)
        ).first()

    # ==================== CALCULOS ====================

    def calculate_spent(self, category_id: int, month: str) -> float:
        start, end = self._month_range(month)
        total = (
            self.session.query(func.sum(Transaction.amount))
            .filter(
                and_(
                    Transaction.category_id == category_id,
                    Transaction.type == "gasto",
                    Transaction.occurred_at >= start,
                    Transaction.occurred_at < end,
                )
            )
            .scalar()
        )
        return float(total or 0.0)

    def check_and_create_alerts(self, category_id: int, month: str) -> Optional[Alert]:
        budget = self.get_budget(category_id, month)
        if not budget:
            return None

        spent = self.calculate_spent(category_id, month)
        ratio = spent / budget.amount if budget.amount > 0 else 0

        severity = None
        threshold = None
        if ratio >= 1.0:
            severity = "critical"
            threshold = 1.0
        elif ratio >= 0.8:
            severity = "warning"
            threshold = 0.8

        if not severity:
            return None

        title = f"Presupuesto {month}"
        message = f"Categoría {category_id}: {spent:.2f} / {budget.amount:.2f}"

        existing = self.session.query(Alert).filter(
            and_(
                Alert.alert_type == "budget",
                Alert.category_id == category_id,
                Alert.title == title,
                Alert.severity == severity,
                Alert.is_dismissed == False,
            )
        ).first()
        if existing:
            return existing

        alert = Alert(
            id=generate_uuid(),
            alert_type="budget",
            severity=severity,
            title=title,
            message=message,
            category_id=category_id,
            amount=spent,
            created_at=datetime.utcnow(),
            synced=False,
        )
        self.session.add(alert)
        self.session.flush()

        self._enqueue_sync("alert", "create", alert.id, self._serialize_alert(alert))
        self.session.commit()
        return alert

    # ==================== HELPERS ====================

    def _validate(self, category_id: int, month: str, amount: float) -> None:
        if amount <= 0:
            raise ValidationError("Monto debe ser positivo")

        category = self.session.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise ValidationError(f"Categoría no encontrada: {category_id}")

        if len(month) != 7 or month[4] != "-":
            raise ValidationError("Mes inválido. Formato esperado YYYY-MM")

    def _month_range(self, month: str) -> Tuple[datetime, datetime]:
        year, mon = month.split("-")
        start = datetime(int(year), int(mon), 1)
        end = start + relativedelta(months=1)
        return start, end

    def _serialize_budget(self, budget: Budget) -> dict:
        return {
            "id": budget.id,
            "category_id": budget.category_id,
            "month": budget.month,
            "amount": str(budget.amount),
        }

    def _serialize_alert(self, alert: Alert) -> dict:
        return {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "category_id": alert.category_id,
            "amount": alert.amount,
            "is_read": alert.is_read,
            "is_dismissed": alert.is_dismissed,
        }

    def _enqueue_sync(self, entity_type: str, operation: str, entity_id: str, payload: dict) -> None:
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type=entity_type,
            operation=operation,
            entity_id=entity_id,
            payload=json.dumps(payload),
            created_at=datetime.utcnow(),
            synced=False,
            sync_error=None,
        )
        self.session.add(outbox)
