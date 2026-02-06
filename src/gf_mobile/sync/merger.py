"""
MergerService

Aplica eventos remotos a la base local con resolución simple de conflictos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Tuple

from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import SyncError
from gf_mobile.persistence.models import (
    Account,
    Alert,
    Budget,
    Category,
    RecurringTransaction,
    SubCategory,
    Tag,
    Transaction,
    TransactionTag,
    SavingsGoal,
    User,
    generate_uuid,
)


class MergerService:
    """Servicio de merge con estrategia last-write-wins."""

    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def apply_events(self, events: Iterable[Dict[str, Any]]) -> Optional[str]:
        """Aplica una lista de eventos y retorna el último timestamp aplicado."""
        session = self.session_factory()
        last_timestamp: Optional[str] = None
        try:
            for event in events:
                self.apply_event(session, event)
                ts = event.get("created_at") or event.get("client_timestamp")
                if ts:
                    last_timestamp = ts
            session.commit()
            return last_timestamp
        except Exception as e:
            session.rollback()
            raise SyncError(f"Error aplicando eventos: {str(e)}")
        finally:
            session.close()

    def apply_event(self, session: Session, event: Dict[str, Any]) -> None:
        event_type = event.get("type")
        payload = event.get("payload") or {}

        # Transactions
        if event_type in {"txn_created", "txn_updated", "txn_deleted"}:
            operation = "delete" if event_type == "txn_deleted" else "update"
            if event_type == "txn_created":
                operation = "create"
            self._merge_transaction(session, operation, payload, event)
            return

        # Budgets
        if event_type in {"budget_created", "budget_updated", "budget_deleted"}:
            operation = "delete" if event_type == "budget_deleted" else "update"
            if event_type == "budget_created":
                operation = "create"
            self._merge_budget(session, operation, payload)
            return

        # Recurring Transactions
        if event_type in {"recurring_created", "recurring_updated", "recurring_deleted"}:
            operation = "delete" if event_type == "recurring_deleted" else "update"
            if event_type == "recurring_created":
                operation = "create"
            self._merge_recurring(session, operation, payload)
            return

        # Alerts
        if event_type in {"alert_created", "alert_updated", "alert_deleted"}:
            operation = "delete" if event_type == "alert_deleted" else "update"
            if event_type == "alert_created":
                operation = "create"
            self._merge_alert(session, operation, payload)
            return

        # Savings Goals
        if event_type in {"goal_created", "goal_updated", "goal_deleted"}:
            operation = "delete" if event_type == "goal_deleted" else "update"
            if event_type == "goal_created":
                operation = "create"
            self._merge_savings_goal(session, operation, payload)
            return

        # Accounts
        if event_type in {"account_created", "account_updated", "account_deleted"}:
            operation = "delete" if event_type == "account_deleted" else "update"
            if event_type == "account_created":
                operation = "create"
            self._merge_account(session, operation, payload)
            return

    # ==================== MERGE HELPERS ====================

    def _is_newer(self, local_dt: Optional[datetime], incoming_iso: Optional[str]) -> bool:
        if not incoming_iso:
            return True
        incoming_dt = self._parse_dt(incoming_iso)
        if not local_dt:
            return True
        return incoming_dt >= local_dt

    def _parse_dt(self, value: Optional[str]) -> datetime:
        if not value:
            return datetime.min
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.min

    def _set_fields(self, obj: Any, payload: Dict[str, Any], fields: Iterable[str]) -> None:
        for f in fields:
            if f in payload:
                setattr(obj, f, payload[f])

    # ==================== ENTITY MERGE ====================

    def _merge_transaction(
        self, session: Session, operation: str, payload: Dict[str, Any], event: Optional[Dict[str, Any]] = None
    ) -> None:
        tx_id = payload.get("transaction_id") or payload.get("id") or (event.get("entityId") if event else None)
        if not tx_id:
            return

        if operation == "delete":
            existing = session.query(Transaction).filter(Transaction.id == tx_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(Transaction).filter(Transaction.id == tx_id).first()
        incoming_updated = payload.get("updated_at") or (event.get("createdAt") if event else None)

        account = self._ensure_account(session, payload.get("account_id"), payload.get("account_name"), payload.get("currency"))
        category = self._ensure_category(session, payload.get("category_id"), payload.get("category_name"))
        subcategory = None
        if payload.get("subcategory_id"):
            subcategory = self._ensure_subcategory(
                session, payload.get("subcategory_id"), payload.get("subcategory_name"), category.id if category else None
            )

        if not existing:
            tx = Transaction(
                id=tx_id,
                account_id=account.id if account else payload.get("account_id"),
                category_id=category.id if category else payload.get("category_id"),
                subcategory_id=subcategory.id if subcategory else payload.get("subcategory_id"),
                type=payload.get("type"),
                amount=float(payload.get("amount")) if payload.get("amount") is not None else 0.0,
                currency=payload.get("currency") or "USD",
                occurred_at=self._parse_dt(payload.get("occurred_at")),
                merchant=payload.get("merchant"),
                note=payload.get("note"),
                synced=True,
                conflict_resolved=True,
                server_id=payload.get("server_id"),
            )
            session.add(tx)
            session.flush()
            self._merge_transaction_tags(session, tx, payload.get("tags", []))
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(
                existing,
                payload,
                [
                    "currency",
                    "type",
                    "merchant",
                    "note",
                    "server_id",
                ],
            )
            if account:
                existing.account_id = account.id
            if category:
                existing.category_id = category.id
            if subcategory:
                existing.subcategory_id = subcategory.id
            if "amount" in payload:
                existing.amount = float(payload["amount"])
            if "occurred_at" in payload:
                existing.occurred_at = self._parse_dt(payload["occurred_at"])
            if incoming_updated:
                existing.updated_at = self._parse_dt(incoming_updated)
            existing.synced = True
            existing.conflict_resolved = True
            self._merge_transaction_tags(session, existing, payload.get("tags", []))

    def _merge_transaction_tags(self, session: Session, tx: Transaction, tag_names: Iterable[str]) -> None:
        if tag_names is None:
            return
        session.query(TransactionTag).filter(TransactionTag.transaction_id == tx.id).delete()
        for name in tag_names:
            tag = session.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = Tag(name=name)
                session.add(tag)
                session.flush()
            session.add(TransactionTag(transaction_id=tx.id, tag_id=tag.id))

    def _ensure_account(
        self, session: Session, account_id: Optional[str], name: Optional[str], currency: Optional[str]
    ) -> Optional[Account]:
        if not account_id:
            return None
        account = session.query(Account).filter(Account.id == account_id).first()
        if account:
            return account
        user = session.query(User).first()
        if not user:
            user = User(name="Usuario")
            session.add(user)
            session.flush()
        account = Account(
            id=account_id,
            user_id=user.id,
            name=name or "Cuenta sincronizada",
            type="efectivo",
            currency=currency or "USD",
            opening_balance=0.0,
            synced=True,
        )
        session.add(account)
        session.flush()
        return account

    def _ensure_category(self, session: Session, sync_id: Optional[str], name: Optional[str]) -> Optional[Category]:
        if not sync_id and name:
            existing = session.query(Category).filter(Category.name == name).first()
            if existing and not existing.sync_id:
                existing.sync_id = generate_uuid()
            return existing
        if not sync_id:
            return None
        category = session.query(Category).filter(Category.sync_id == sync_id).first()
        if category:
            return category
        category = Category(
            sync_id=sync_id,
            name=name or "Sin categoría",
            budget_group="Otros",
        )
        session.add(category)
        session.flush()
        return category

    def _ensure_subcategory(
        self, session: Session, sync_id: str, name: Optional[str], category_id: Optional[int]
    ) -> Optional[SubCategory]:
        subcategory = session.query(SubCategory).filter(SubCategory.sync_id == sync_id).first()
        if subcategory:
            return subcategory
        if not category_id:
            return None
        subcategory = SubCategory(
            sync_id=sync_id,
            category_id=category_id,
            name=name or "Sin subcategoría",
        )
        session.add(subcategory)
        session.flush()
        return subcategory

    def _merge_budget(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        budget_id = payload.get("id")
        if not budget_id:
            return
        if operation == "delete":
            existing = session.query(Budget).filter(Budget.id == budget_id).first()
            if existing:
                session.delete(existing)
            return
        existing = session.query(Budget).filter(Budget.id == budget_id).first()
        incoming_updated = payload.get("updated_at") or payload.get("client_timestamp")

        if not existing:
            budget = Budget(
                id=budget_id,
                category_id=payload.get("category_id"),
                month=payload.get("month"),
                amount=float(payload.get("amount")) if payload.get("amount") is not None else 0.0,
                synced=True,
                server_id=payload.get("server_id"),
            )
            session.add(budget)
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(existing, payload, ["category_id", "month", "server_id"])
            if "amount" in payload:
                existing.amount = float(payload["amount"])
            existing.synced = True

    def _merge_recurring(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        recurring_id = payload.get("id")
        if not recurring_id:
            return
        if operation == "delete":
            existing = session.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(RecurringTransaction).filter(RecurringTransaction.id == recurring_id).first()
        incoming_updated = payload.get("updated_at") or payload.get("client_timestamp")

        if not existing:
            recurring = RecurringTransaction(
                id=recurring_id,
                name=payload.get("name"),
                type=payload.get("type"),
                amount=float(payload.get("amount")) if payload.get("amount") is not None else 0.0,
                currency=payload.get("currency") or "USD",
                category_id=payload.get("category_id"),
                subcategory_id=payload.get("subcategory_id"),
                account_id=payload.get("account_id"),
                frequency=payload.get("frequency"),
                start_date=self._parse_dt(payload.get("start_date")),
                end_date=self._parse_dt(payload.get("end_date")) if payload.get("end_date") else None,
                auto_generate=payload.get("auto_generate", False),
                next_run=self._parse_dt(payload.get("next_run")) if payload.get("next_run") else None,
                synced=True,
                server_id=payload.get("server_id"),
            )
            session.add(recurring)
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(
                existing,
                payload,
                [
                    "name",
                    "type",
                    "currency",
                    "category_id",
                    "subcategory_id",
                    "account_id",
                    "frequency",
                    "auto_generate",
                    "server_id",
                ],
            )
            if "amount" in payload:
                existing.amount = float(payload["amount"])
            if "start_date" in payload:
                existing.start_date = self._parse_dt(payload["start_date"])
            if "end_date" in payload:
                existing.end_date = self._parse_dt(payload["end_date"]) if payload["end_date"] else None
            if "next_run" in payload:
                existing.next_run = self._parse_dt(payload["next_run"]) if payload["next_run"] else None
            existing.synced = True

    def _merge_account(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        account_id = payload.get("id")
        if not account_id:
            return
        if operation == "delete":
            existing = session.query(Account).filter(Account.id == account_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(Account).filter(Account.id == account_id).first()
        incoming_updated = payload.get("updated_at") or payload.get("client_timestamp")

        if not existing:
            account = Account(
                id=account_id,
                user_id=payload.get("user_id"),
                name=payload.get("name"),
                type=payload.get("type"),
                currency=payload.get("currency") or "USD",
                opening_balance=float(payload.get("opening_balance")) if payload.get("opening_balance") is not None else 0.0,
                synced=True,
                server_id=payload.get("server_id"),
            )
            session.add(account)
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(existing, payload, ["user_id", "name", "type", "currency", "server_id"])
            if "opening_balance" in payload:
                existing.opening_balance = float(payload["opening_balance"])
            existing.synced = True

    def _merge_category(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        category_id = payload.get("id")
        if category_id is None:
            return
        if operation == "delete":
            existing = session.query(Category).filter(Category.id == category_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(Category).filter(Category.id == category_id).first()
        if not existing:
            category = Category(
                id=category_id,
                name=payload.get("name"),
                budget_group=payload.get("budget_group"),
            )
            session.add(category)
            return

        self._set_fields(existing, payload, ["name", "budget_group"])

    def _merge_subcategory(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        subcategory_id = payload.get("id")
        if subcategory_id is None:
            return
        if operation == "delete":
            existing = session.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(SubCategory).filter(SubCategory.id == subcategory_id).first()
        if not existing:
            sub = SubCategory(
                id=subcategory_id,
                category_id=payload.get("category_id"),
                name=payload.get("name"),
            )
            session.add(sub)
            return

        self._set_fields(existing, payload, ["category_id", "name"])

    def _merge_tag(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        tag_id = payload.get("id")
        if tag_id is None:
            return
        if operation == "delete":
            existing = session.query(Tag).filter(Tag.id == tag_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(Tag).filter(Tag.id == tag_id).first()
        if not existing:
            tag = Tag(id=tag_id, name=payload.get("name"))
            session.add(tag)
            return

        self._set_fields(existing, payload, ["name"])

    def _merge_alert(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        alert_id = payload.get("id")
        if not alert_id:
            return
        if operation == "delete":
            existing = session.query(Alert).filter(Alert.id == alert_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(Alert).filter(Alert.id == alert_id).first()
        incoming_updated = payload.get("updated_at") or payload.get("client_timestamp")

        if not existing:
            alert = Alert(
                id=alert_id,
                alert_type=payload.get("alert_type"),
                severity=payload.get("severity"),
                title=payload.get("title"),
                message=payload.get("message"),
                transaction_id=payload.get("transaction_id"),
                category_id=payload.get("category_id"),
                amount=payload.get("amount"),
                is_read=payload.get("is_read", False),
                is_dismissed=payload.get("is_dismissed", False),
                synced=True,
                server_id=payload.get("server_id"),
            )
            session.add(alert)
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(
                existing,
                payload,
                [
                    "alert_type",
                    "severity",
                    "title",
                    "message",
                    "transaction_id",
                    "category_id",
                    "amount",
                    "is_read",
                    "is_dismissed",
                    "server_id",
                ],
            )
            existing.synced = True

    def _merge_savings_goal(self, session: Session, operation: str, payload: Dict[str, Any]) -> None:
        goal_id = payload.get("id")
        if not goal_id:
            return
        if operation == "delete":
            existing = session.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
            if existing:
                session.delete(existing)
            return

        existing = session.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
        incoming_updated = payload.get("updated_at") or payload.get("client_timestamp")

        if not existing:
            goal = SavingsGoal(
                id=goal_id,
                user_id=payload.get("user_id"),
                name=payload.get("name"),
                target_amount=float(payload.get("target_amount")) if payload.get("target_amount") is not None else 0.0,
                current_amount=float(payload.get("current_amount")) if payload.get("current_amount") is not None else 0.0,
                deadline=self._parse_dt(payload.get("deadline")) if payload.get("deadline") else None,
                synced=True,
                server_id=payload.get("server_id"),
            )
            session.add(goal)
            return

        if self._is_newer(existing.updated_at, incoming_updated):
            self._set_fields(existing, payload, ["user_id", "name", "server_id"])
            if "target_amount" in payload:
                existing.target_amount = float(payload["target_amount"])
            if "current_amount" in payload:
                existing.current_amount = float(payload["current_amount"])
            if "deadline" in payload:
                existing.deadline = self._parse_dt(payload["deadline"]) if payload["deadline"] else None
            existing.synced = True
