"""
RecurringService

Gestiona transacciones recurrentes y generación automática.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import ValidationError, DatabaseError
from gf_mobile.persistence.models import (
    RecurringTransaction,
    Transaction,
    Account,
    Category,
    SyncOutbox,
    generate_uuid,
)


class RecurringService:
    """Servicio para transacciones recurrentes."""

    def __init__(self, session: Session):
        self.session = session

    # ==================== CRUD ====================

    def create(
        self,
        name: str,
        type_: str,
        amount: float,
        currency: str,
        category_id: int,
        account_id: str,
        frequency: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
        auto_generate: bool = False,
    ) -> RecurringTransaction:
        try:
            self._validate_input(type_, amount, category_id, account_id, frequency)

            recurring = RecurringTransaction(
                name=name,
                type=type_,
                amount=amount,
                currency=currency,
                category_id=category_id,
                account_id=account_id,
                frequency=frequency,
                start_date=start_date,
                end_date=end_date,
                auto_generate=auto_generate,
                next_run=start_date,
                synced=False,
            )

            self.session.add(recurring)
            self.session.flush()

            self._enqueue_sync(
                entity_type="recurring",
                operation="create",
                entity_id=str(recurring.id),
                payload=self._serialize_recurring(recurring),
            )

            self.session.commit()
            return recurring

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al crear recurrente: {str(e)}")

    def update(self, recurring_id: int, **kwargs: Any) -> RecurringTransaction:
        try:
            recurring = self.get_by_id(recurring_id)
            if not recurring:
                raise ValidationError(f"Recurrente no encontrada: {recurring_id}")

            allowed = {
                "name",
                "type",
                "amount",
                "currency",
                "category_id",
                "account_id",
                "frequency",
                "start_date",
                "end_date",
                "auto_generate",
                "next_run",
            }

            for key, value in kwargs.items():
                if key not in allowed:
                    raise ValidationError(f"Campo no permitido: {key}")
                if value is not None:
                    setattr(recurring, key, value)

            recurring.synced = False
            self.session.flush()

            self._enqueue_sync(
                entity_type="recurring",
                operation="update",
                entity_id=str(recurring.id),
                payload=self._serialize_recurring(recurring),
            )

            self.session.commit()
            return recurring

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al actualizar recurrente: {str(e)}")

    def delete(self, recurring_id: int) -> bool:
        try:
            recurring = self.get_by_id(recurring_id)
            if not recurring:
                raise ValidationError(f"Recurrente no encontrada: {recurring_id}")

            self._enqueue_sync(
                entity_type="recurring",
                operation="delete",
                entity_id=str(recurring.id),
                payload={},
            )

            self.session.delete(recurring)
            self.session.commit()
            return True

        except ValidationError:
            self.session.rollback()
            raise
        except Exception as e:
            self.session.rollback()
            raise DatabaseError(f"Error al eliminar recurrente: {str(e)}")

    def get_by_id(self, recurring_id: int) -> Optional[RecurringTransaction]:
        return self.session.query(RecurringTransaction).filter(
            RecurringTransaction.id == recurring_id
        ).first()

    def list_all(self) -> List[RecurringTransaction]:
        return self.session.query(RecurringTransaction).order_by(RecurringTransaction.next_run).all()

    # ==================== GENERATION ====================

    def generate_due_transactions(
        self,
        as_of: Optional[datetime] = None,
        waterline_ts: Optional[datetime] = None,
    ) -> int:
        """Genera transacciones recurrentes vencidas.

        Si waterline_ts está definido, solo genera si next_run <= waterline_ts.
        """
        if as_of is None:
            as_of = datetime.utcnow()

        due_query = self.session.query(RecurringTransaction).filter(
            and_(
                RecurringTransaction.auto_generate == True,
                RecurringTransaction.next_run != None,
                RecurringTransaction.next_run <= as_of,
            )
        )

        if waterline_ts is not None:
            due_query = due_query.filter(RecurringTransaction.next_run <= waterline_ts)

        due_items = due_query.all()
        created = 0

        for recurring in due_items:
            next_run = recurring.next_run
            if recurring.end_date and next_run and next_run > recurring.end_date:
                continue

            if next_run and self._exists_transaction(recurring.id, next_run):
                recurring.next_run = self.compute_next_run(next_run, recurring.frequency)
                continue

            tx = Transaction(
                id=generate_uuid(),
                account_id=recurring.account_id,
                category_id=recurring.category_id,
                subcategory_id=recurring.subcategory_id,
                recurring_id=recurring.id,
                type=recurring.type,
                amount=recurring.amount,
                currency=recurring.currency,
                occurred_at=next_run or as_of,
                note=f"Recurrente: {recurring.name}",
                synced=False,
            )
            self.session.add(tx)
            self.session.flush()

            self._enqueue_sync(
                entity_type="transaction",
                operation="create",
                entity_id=tx.id,
                payload=self._serialize_transaction(tx),
            )

            recurring.next_run = self.compute_next_run(next_run or as_of, recurring.frequency)
            recurring.synced = False

            self._enqueue_sync(
                entity_type="recurring",
                operation="update",
                entity_id=str(recurring.id),
                payload=self._serialize_recurring(recurring),
            )

            created += 1

        self.session.commit()
        return created

    def compute_next_run(self, last_run: datetime, frequency: str) -> datetime:
        if frequency == "weekly":
            return last_run + timedelta(weeks=1)
        if frequency == "monthly":
            return last_run + relativedelta(months=1)
        if frequency.startswith("monthly:"):
            months = int(frequency.split(":")[1])
            return last_run + relativedelta(months=months)
        if frequency == "annual":
            return last_run + relativedelta(years=1)
        raise ValidationError(f"Frecuencia inválida: {frequency}")

    # ==================== INTERNALS ====================

    def _validate_input(
        self,
        type_: str,
        amount: float,
        category_id: int,
        account_id: str,
        frequency: str,
    ) -> None:
        valid_types = {"ingreso", "gasto", "transferencia"}
        if type_ not in valid_types:
            raise ValidationError(f"Tipo inválido: {type_}")
        if amount <= 0:
            raise ValidationError("Monto debe ser positivo")

        account = self.session.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValidationError(f"Cuenta no encontrada: {account_id}")

        category = self.session.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise ValidationError(f"Categoría no encontrada: {category_id}")

        valid_freq = {"weekly", "monthly", "annual"}
        if frequency not in valid_freq and not frequency.startswith("monthly:"):
            raise ValidationError(f"Frecuencia inválida: {frequency}")

    def _exists_transaction(self, recurring_id: int, run_date: datetime) -> bool:
        start = datetime(run_date.year, run_date.month, run_date.day)
        end = start + timedelta(days=1)
        count = (
            self.session.query(func.count(Transaction.id))
            .filter(
                and_(
                    Transaction.recurring_id == recurring_id,
                    Transaction.occurred_at >= start,
                    Transaction.occurred_at < end,
                )
            )
            .scalar()
        )
        return (count or 0) > 0

    def _serialize_recurring(self, recurring: RecurringTransaction) -> Dict[str, Any]:
        return {
            "id": recurring.id,
            "name": recurring.name,
            "type": recurring.type,
            "amount": str(recurring.amount),
            "currency": recurring.currency,
            "category_id": recurring.category_id,
            "subcategory_id": recurring.subcategory_id,
            "account_id": recurring.account_id,
            "frequency": recurring.frequency,
            "start_date": recurring.start_date.isoformat() if recurring.start_date else None,
            "end_date": recurring.end_date.isoformat() if recurring.end_date else None,
            "auto_generate": recurring.auto_generate,
            "next_run": recurring.next_run.isoformat() if recurring.next_run else None,
        }

    def _serialize_transaction(self, tx: Transaction) -> Dict[str, Any]:
        return {
            "id": tx.id,
            "account_id": tx.account_id,
            "category_id": tx.category_id,
            "subcategory_id": tx.subcategory_id,
            "type": tx.type,
            "amount": str(tx.amount),
            "currency": tx.currency,
            "occurred_at": tx.occurred_at.isoformat() if tx.occurred_at else None,
            "note": tx.note,
        }

    def _enqueue_sync(
        self,
        entity_type: str,
        operation: str,
        entity_id: str,
        payload: Dict[str, Any],
    ) -> None:
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
