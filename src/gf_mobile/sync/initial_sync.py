"""
InitialSyncService

Maneja la sincronizaciÃ³n inicial de datos base desde Firestore.
Se ejecuta una sola vez al primer login en el dispositivo mÃ³vil.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import SyncError
from gf_mobile.core.transaction_types import normalize_transaction_type
from gf_mobile.persistence.models import Account, Category, Budget, Transaction, SyncState, User
from gf_mobile.sync.firestore_client import FirestoreClient


class InitialSyncService:
    """
    Sincroniza todos los datos base desde Firestore la primera vez.
    
    1. Descarga todas las cuentas (accounts)
    2. Descarga todas las categorÃ­as
    3. Descarga todos los presupuestos
    4. Descarga todas las transacciones existentes
    5. Marca como completada la sincronizaciÃ³n inicial
    """

    def __init__(
        self,
        session_factory,
        firestore_client: FirestoreClient,
        user_uid: str,
        user_id: Optional[int] = None,
    ):
        self.session_factory = session_factory
        self.firestore_client = firestore_client
        self.user_uid = user_uid
        self.user_id = user_id

    def _state_key(self, base_key: str) -> str:
        """Clave de estado namespaced por usuario remoto para evitar cruces entre cuentas."""
        suffix = (self.user_uid or "").strip()
        return f"{base_key}:{suffix}" if suffix else base_key

    def needs_initial_sync(self) -> bool:
        """Verifica si es la primera sincronizacion para el usuario actual."""
        session = self.session_factory()
        try:
            state_key = self._state_key("initial_sync_completed")
            state = session.query(SyncState).filter(
                SyncState.key == state_key
            ).first()

            if state and state.value == "true":
                # Fallback seguro: si no hay transacciones locales, reintentar sync inicial.
                # Esto evita quedar "bloqueado" si una sync inicial previa se marco completa
                # pero no trajo movimientos remotos.
                has_local_transaction = session.query(Transaction.id).first() is not None
                if not has_local_transaction:
                    return True
                has_local_account = session.query(Account.id).filter(
                    Account.user_id == self.user_id
                ).first() is not None
                has_local_category = session.query(Category.id).first() is not None
                return not (has_local_account and has_local_category and has_local_transaction)

            return True
        finally:
            session.close()

    async def perform_initial_sync(self) -> Dict[str, int]:
        return await self.perform_snapshot_sync(mark_completed=True)

    async def perform_snapshot_sync(self, *, mark_completed: bool = False) -> Dict[str, int]:
        """
        Realiza una sincronizaciÃ³n de snapshot de todos los datos base.
        
        Returns:
            Dict con contadores de datos importados
        """
        session = self.session_factory()
        try:
            imported = {
                "accounts": 0,
                "categories": 0,
                "budgets": 0,
                "transactions": 0,
            }

            # 1. Descargar y aplicar cuentas
            imported["accounts"] = await self._sync_accounts(session)
            
            # 2. Descargar y aplicar categorÃ­as
            imported["categories"] = await self._sync_categories(session)
            
            # 3. Descargar y aplicar presupuestos
            imported["budgets"] = await self._sync_budgets(session)
            
            # 4. Descargar y aplicar transacciones
            imported["transactions"] = await self._sync_transactions(session)
            
            if mark_completed:
                self._mark_initial_sync_completed(session)
            
            session.commit()
            return imported

        except Exception as e:
            session.rollback()
            raise SyncError(f"Error en sincronizaciÃ³n inicial: {str(e)}")
        finally:
            session.close()

    async def _sync_accounts(self, session: Session) -> int:
        """Descarga y aplica todas las cuentas."""
        try:
            local_user_id = self._resolve_local_user_id(session)
            accounts_data = await self.firestore_client.get_all_accounts(
                user_uid=self.user_uid
            )
            
            count = 0
            seen_remote_ids: set[str] = set()
            for account_data in accounts_data:
                remote_id = self._string_id(account_data.get("sync_id") or account_data.get("id"))
                if not remote_id:
                    continue
                seen_remote_ids.add(remote_id)

                account = self._find_local_account(session, remote_id)
                if not account:
                    account = Account(
                        user_id=local_user_id,
                        server_id=remote_id,
                        synced=True,
                    )
                    session.add(account)
                    count += 1

                account.name = account_data.get("name") or account.name or "Cuenta"
                account.type = account_data.get("type") or account.type or "efectivo"
                account.currency = account_data.get("currency", "EUR") or account.currency or "EUR"
                account.opening_balance = float(account_data.get("opening_balance", 0) or 0)
                account.synced = True
                if not account.server_id:
                    account.server_id = remote_id
                self._merge_duplicate_accounts(session, account, remote_id)

            self._dedupe_accounts_for_snapshot(session, seen_remote_ids)
            
            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando cuentas: {str(e)}")

    async def _sync_categories(self, session: Session) -> int:
        """Descarga y aplica todas las categorÃ­as."""
        try:
            categories_data = await self.firestore_client.get_all_categories(
                user_uid=self.user_uid
            )
            
            count = 0
            for cat_data in categories_data:
                remote_sync_id = str(cat_data.get("sync_id") or cat_data.get("id") or "")
                name = (cat_data.get("name") or "").strip()
                budget_group = (cat_data.get("budget_group") or "Otros").strip() or "Otros"
                if not name:
                    continue
                existing = None
                if remote_sync_id:
                    existing = session.query(Category).filter(
                        Category.sync_id == remote_sync_id
                    ).first()
                if not existing:
                    existing = session.query(Category).filter(
                        func.lower(func.trim(Category.name)) == name.lower(),
                        func.lower(func.trim(Category.budget_group)) == budget_group.lower(),
                    ).first()
                if existing:
                    # Si ya existia por nombre+grupo, completar sync_id para mapear bien.
                    if remote_sync_id and not existing.sync_id:
                        existing.sync_id = remote_sync_id
                    existing.name = name
                    existing.budget_group = budget_group
                    continue

                category = Category(
                    name=name,
                    budget_group=budget_group,
                    sync_id=remote_sync_id or None,
                )
                session.add(category)
                count += 1
            
            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando categorÃ­as: {str(e)}")

    async def _sync_budgets(self, session: Session) -> int:
        """Descarga y aplica todos los presupuestos."""
        try:
            budgets_data = await self.firestore_client.get_all_budgets(
                user_uid=self.user_uid
            )
            
            count = 0
            seen_budget_ids: set[str] = set()
            for budget_data in budgets_data:
                budget_id = budget_data.get("id")
                if budget_id:
                    seen_budget_ids.add(str(budget_id))
                local_category_id = self._resolve_local_category_id(
                    session, budget_data.get("category_id")
                )
                if local_category_id is None:
                    # Presupuesto invÃ¡lido sin categorÃ­a local mapeable.
                    continue

                budget = session.query(Budget).filter(Budget.id == budget_id).first() if budget_id else None
                if not budget:
                    budget = session.query(Budget).filter(
                        Budget.category_id == local_category_id,
                        Budget.month == budget_data.get("month"),
                    ).first()

                if not budget:
                    budget = Budget(
                        id=budget_id,
                        category_id=local_category_id,
                        month=budget_data.get("month"),
                        amount=float(budget_data.get("amount", 0)),
                        synced=True,
                    )
                    session.add(budget)
                    count += 1
                else:
                    budget.category_id = local_category_id
                    budget.month = budget_data.get("month")
                    budget.amount = float(budget_data.get("amount", 0) or 0)
                    budget.synced = True

            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando presupuestos: {str(e)}")

    async def _sync_transactions(self, session: Session) -> int:
        """Descarga y aplica todas las transacciones."""
        try:
            transactions_data = await self.firestore_client.get_all_transactions(
                user_uid=self.user_uid
            )
            
            count = 0
            seen_tx_ids: set[str] = set()
            seen_server_ids: set[str] = set()
            for tx_data in transactions_data:
                remote_doc_id = self._string_id(tx_data.get("id"))
                remote_sync_id = self._string_id(
                    tx_data.get("sync_id") or tx_data.get("transaction_id")
                )
                local_tx_id = remote_sync_id or remote_doc_id
                if not local_tx_id:
                    continue
                seen_tx_ids.add(local_tx_id)
                if remote_doc_id:
                    seen_server_ids.add(remote_doc_id)

                existing = self._find_local_transaction(
                    session,
                    local_tx_id=local_tx_id,
                    remote_doc_id=remote_doc_id,
                )
                local_category_id = self._resolve_local_category_id(
                    session, tx_data.get("category_id")
                )
                local_account_id = self._resolve_local_account_id(
                    session, tx_data.get("account_id")
                )
                local_to_account_id = self._resolve_local_account_id(
                    session, tx_data.get("to_account_id")
                )
                if local_category_id is None:
                    continue
                if local_account_id is None:
                    continue

                occurred_at = self._parse_remote_datetime(tx_data.get("occurred_at"))
                if occurred_at is None:
                    continue

                if not existing:
                    transaction = Transaction(
                        id=local_tx_id,
                        account_id=local_account_id,
                        to_account_id=local_to_account_id,
                        category_id=local_category_id,
                        type=normalize_transaction_type(tx_data.get("type")),
                        amount=float(tx_data.get("amount", 0) or 0),
                        currency=tx_data.get("currency", "EUR"),
                        occurred_at=occurred_at,
                        merchant=tx_data.get("merchant"),
                        note=tx_data.get("note"),
                        synced=True,
                        server_id=remote_doc_id or None,
                    )
                    session.add(transaction)
                    count += 1
                else:
                    if existing.id != local_tx_id and remote_sync_id:
                        existing.id = local_tx_id
                    existing.account_id = local_account_id
                    existing.to_account_id = local_to_account_id
                    existing.category_id = local_category_id
                    existing.type = normalize_transaction_type(tx_data.get("type"))
                    existing.amount = float(tx_data.get("amount", 0) or 0)
                    existing.currency = tx_data.get("currency", "EUR")
                    existing.occurred_at = occurred_at
                    existing.merchant = tx_data.get("merchant")
                    existing.note = tx_data.get("note")
                    existing.synced = True
                    if remote_doc_id:
                        existing.server_id = remote_doc_id

            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando transacciones: {str(e)}")

    def _resolve_local_category_id(
        self, session: Session, remote_category_id: Optional[Any]
    ) -> Optional[int]:
        """
        Convierte category_id remoto (normalmente sync_id) a Category.id local.
        """
        if remote_category_id is None:
            return None
        remote_value = str(remote_category_id).strip()
        if not remote_value:
            return None

        # Intentar por sync_id primero (payload de sync usa sync_id).
        cat = session.query(Category).filter(Category.sync_id == remote_value).first()
        if cat:
            return cat.id

        # Compatibilidad: si vino como id numÃ©rico local serializado.
        if remote_value.isdigit():
            cat = session.query(Category).filter(Category.id == int(remote_value)).first()
            if cat:
                return cat.id

        return None

    def _resolve_local_account_id(
        self, session: Session, remote_account_id: Optional[Any]
    ) -> Optional[str]:
        remote_value = self._string_id(remote_account_id)
        if not remote_value:
            return None

        account = self._find_local_account(session, remote_value)
        return account.id if account else None

    def _find_local_account(self, session: Session, remote_id: str) -> Optional[Account]:
        account = session.query(Account).filter(Account.server_id == remote_id).first()
        if account:
            return account
        return session.query(Account).filter(Account.id == remote_id).first()

    def _merge_duplicate_accounts(
        self,
        session: Session,
        primary_account: Account,
        remote_id: str,
    ) -> None:
        duplicates = session.query(Account).filter(
            ((Account.server_id == remote_id) | (Account.id == remote_id)),
            Account.id != primary_account.id,
        ).all()
        for duplicate in duplicates:
            session.query(Transaction).filter(Transaction.account_id == duplicate.id).update(
                {Transaction.account_id: primary_account.id},
                synchronize_session=False,
            )
            session.query(Transaction).filter(Transaction.to_account_id == duplicate.id).update(
                {Transaction.to_account_id: primary_account.id},
                synchronize_session=False,
            )
            session.delete(duplicate)

    def _find_local_transaction(
        self,
        session: Session,
        *,
        local_tx_id: str,
        remote_doc_id: str,
    ) -> Optional[Transaction]:
        transaction = session.query(Transaction).filter(Transaction.id == local_tx_id).first()
        if transaction:
            return transaction
        if remote_doc_id:
            transaction = session.query(Transaction).filter(
                Transaction.server_id == remote_doc_id
            ).first()
            if transaction:
                return transaction
        return None

    def _dedupe_accounts_for_snapshot(self, session: Session, seen_remote_ids: set[str]) -> None:
        for remote_id in seen_remote_ids:
            accounts = session.query(Account).filter(
                (Account.server_id == remote_id) | (Account.id == remote_id)
            ).all()
            if len(accounts) <= 1:
                continue
            primary = next((account for account in accounts if account.server_id == remote_id), accounts[0])
            for duplicate in accounts:
                if duplicate.id == primary.id:
                    continue
                session.query(Transaction).filter(Transaction.account_id == duplicate.id).update(
                    {Transaction.account_id: primary.id},
                    synchronize_session=False,
                )
                session.query(Transaction).filter(Transaction.to_account_id == duplicate.id).update(
                    {Transaction.to_account_id: primary.id},
                    synchronize_session=False,
                )
                session.delete(duplicate)

    def _resolve_local_user_id(self, session: Session) -> int:
        if self.user_id is not None:
            return self.user_id

        user = None
        if self.user_uid:
            user = session.query(User).filter(User.server_uid == self.user_uid).first()
        if not user:
            user = session.query(User).first()
        if not user:
            raise SyncError("No hay usuario local para importar snapshot remoto")
        self.user_id = user.id
        return user.id

    @staticmethod
    def _parse_remote_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    @staticmethod
    def _string_id(value: Optional[Any]) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _mark_initial_sync_completed(self, session: Session) -> None:
        """Marca la sincronizacion inicial como completada para el usuario actual."""
        completed_key = self._state_key("initial_sync_completed")
        state = session.query(SyncState).filter(
            SyncState.key == completed_key
        ).first()

        if not state:
            state = SyncState(key=completed_key, value="true")
            session.add(state)
        else:
            state.value = "true"

