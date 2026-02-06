"""
InitialSyncService

Maneja la sincronización inicial de datos base desde Firestore.
Se ejecuta una sola vez al primer login en el dispositivo móvil.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import SyncError
from gf_mobile.persistence.models import (
    Account, Category, Budget, Transaction, SyncState, AppliedEvent
)
from gf_mobile.sync.firestore_client import FirestoreClient


class InitialSyncService:
    """
    Sincroniza todos los datos base desde Firestore la primera vez.
    
    1. Descarga todas las cuentas (accounts)
    2. Descarga todas las categorías
    3. Descarga todos los presupuestos
    4. Descarga todas las transacciones existentes
    5. Marca como completada la sincronización inicial
    """

    def __init__(
        self,
        session_factory,
        firestore_client: FirestoreClient,
        user_uid: str,
        user_id: int,
    ):
        self.session_factory = session_factory
        self.firestore_client = firestore_client
        self.user_uid = user_uid
        self.user_id = user_id

    def needs_initial_sync(self) -> bool:
        """Verifica si es la primera sincronización."""
        session = self.session_factory()
        try:
            state = session.query(SyncState).filter(
                SyncState.key == "initial_sync_completed"
            ).first()
            return not state or state.value != "true"
        finally:
            session.close()

    async def perform_initial_sync(self) -> Dict[str, int]:
        """
        Realiza la sincronización inicial de todos los datos base.
        
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
            
            # 2. Descargar y aplicar categorías
            imported["categories"] = await self._sync_categories(session)
            
            # 3. Descargar y aplicar presupuestos
            imported["budgets"] = await self._sync_budgets(session)
            
            # 4. Descargar y aplicar transacciones
            imported["transactions"] = await self._sync_transactions(session)
            
            # Marcar como completada
            self._mark_initial_sync_completed(session)
            
            session.commit()
            return imported

        except Exception as e:
            session.rollback()
            raise SyncError(f"Error en sincronización inicial: {str(e)}")
        finally:
            session.close()

    async def _sync_accounts(self, session: Session) -> int:
        """Descarga y aplica todas las cuentas."""
        try:
            accounts_data = await self.firestore_client.get_all_accounts(
                user_uid=self.user_uid
            )
            
            count = 0
            for account_data in accounts_data:
                account_id = account_data.get("id")
                if session.query(Account).filter(Account.id == account_id).first():
                    continue  # Ya existe
                
                account = Account(
                    id=account_data.get("id"),
                    user_id=self.user_id,
                    name=account_data.get("name"),
                    type=account_data.get("type"),
                    currency=account_data.get("currency", "EUR"),
                    opening_balance=float(account_data.get("opening_balance", 0)),
                    synced=True,
                )
                session.add(account)
                count += 1
            
            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando cuentas: {str(e)}")

    async def _sync_categories(self, session: Session) -> int:
        """Descarga y aplica todas las categorías."""
        try:
            categories_data = await self.firestore_client.get_all_categories(
                user_uid=self.user_uid
            )
            
            count = 0
            for cat_data in categories_data:
                cat_id = cat_data.get("id")
                if session.query(Category).filter(Category.id == cat_id).first():
                    continue  # Ya existe
                
                category = Category(
                    id=cat_id,
                    name=cat_data.get("name"),
                    budget_group=cat_data.get("budget_group", "Otros"),
                    synced=True,
                )
                session.add(category)
                count += 1
            
            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando categorías: {str(e)}")

    async def _sync_budgets(self, session: Session) -> int:
        """Descarga y aplica todos los presupuestos."""
        try:
            budgets_data = await self.firestore_client.get_all_budgets(
                user_uid=self.user_uid
            )
            
            count = 0
            for budget_data in budgets_data:
                budget_id = budget_data.get("id")
                if session.query(Budget).filter(Budget.id == budget_id).first():
                    continue  # Ya existe
                
                budget = Budget(
                    id=budget_id,
                    category_id=budget_data.get("category_id"),
                    month=budget_data.get("month"),
                    amount=float(budget_data.get("amount", 0)),
                    synced=True,
                )
                session.add(budget)
                count += 1
            
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
            for tx_data in transactions_data:
                tx_id = tx_data.get("id")
                if session.query(Transaction).filter(Transaction.id == tx_id).first():
                    continue  # Ya existe
                
                transaction = Transaction(
                    id=tx_id,
                    account_id=tx_data.get("account_id"),
                    category_id=tx_data.get("category_id"),
                    type=tx_data.get("type"),
                    amount=float(tx_data.get("amount", 0)),
                    currency=tx_data.get("currency", "EUR"),
                    occurred_at=datetime.fromisoformat(tx_data.get("occurred_at")),
                    merchant=tx_data.get("merchant"),
                    note=tx_data.get("note"),
                    synced=True,
                )
                session.add(transaction)
                count += 1
            
            return count
        except Exception as e:
            raise SyncError(f"Error sincronizando transacciones: {str(e)}")

    def _mark_initial_sync_completed(self, session: Session) -> None:
        """Marca la sincronización inicial como completada."""
        state = session.query(SyncState).filter(
            SyncState.key == "initial_sync_completed"
        ).first()
        
        if not state:
            state = SyncState(key="initial_sync_completed", value="true")
            session.add(state)
        else:
            state.value = "true"
        
        # Actualizar timestamp de última sincronización
        last_sync = session.query(SyncState).filter(
            SyncState.key == "last_applied_at"
        ).first()
        if not last_sync:
            last_sync = SyncState(
                key="last_applied_at",
                value=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            )
            session.add(last_sync)
        else:
            last_sync.value = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
