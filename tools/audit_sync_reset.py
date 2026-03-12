from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from gf_mobile.core.auth import AuthService
from gf_mobile.core.config import get_settings
from gf_mobile.core.session_manager import SessionManager
from gf_mobile.persistence.db import init_database, build_session_factory
from gf_mobile.persistence.models import User, Account, Budget, Category, Transaction, SyncState
from gf_mobile.services.transaction_service import TransactionService
from gf_mobile.sync.firestore_client import FirestoreClient
from gf_mobile.sync.initial_sync import InitialSyncService
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.simple_sync import SimpleSyncService


DESKTOP_DB = Path.home() / ".gestionfondos" / "gestionfondos.db"


@dataclass
class BalanceRow:
    name: str
    opening_balance: float
    current_balance: float


def _delete_mobile_db(settings) -> None:
    for suffix in ("", "-wal", "-shm"):
        path = Path(str(settings.DB_PATH) + suffix)
        if path.exists():
            path.unlink()


def _ensure_local_user(session_factory, user_uid: str) -> int:
    session = session_factory()
    try:
        user = session.query(User).filter(User.server_uid == user_uid).first()
        if not user:
            user = session.query(User).first()
        if not user:
            user = User(name="Usuario", server_uid=user_uid)
            session.add(user)
            session.commit()
        elif user.server_uid != user_uid:
            user.server_uid = user_uid
            session.commit()
        return int(user.id)
    finally:
        session.close()


def _mobile_stats(session_factory) -> dict[str, Any]:
    session = session_factory()
    try:
        tx_service = TransactionService(session, user_id=1)
        accounts = session.query(Account).order_by(Account.name).all()
        return {
            "counts": {
                "accounts": session.query(Account).count(),
                "categories": session.query(Category).count(),
                "budgets": session.query(Budget).count(),
                "transactions": session.query(Transaction).count(),
            },
            "balances": [
                asdict(
                    BalanceRow(
                        name=account.name,
                        opening_balance=float(account.opening_balance or 0.0),
                        current_balance=float(tx_service.balance_for_account(account.id)),
                    )
                )
                for account in accounts
            ],
            "transactions": [
                {
                    "id": tx.id,
                    "server_id": tx.server_id,
                    "type": tx.type,
                    "amount": float(tx.amount or 0.0),
                    "account_id": tx.account_id,
                    "to_account_id": tx.to_account_id,
                    "category_id": tx.category_id,
                    "occurred_at": tx.occurred_at.isoformat() if tx.occurred_at else None,
                    "merchant": tx.merchant,
                }
                for tx in session.query(Transaction).order_by(Transaction.occurred_at.desc()).all()
            ],
            "sync_state": {
                row.key: row.value for row in session.query(SyncState).all()
            },
        }
    finally:
        session.close()


def _desktop_stats() -> dict[str, Any]:
    if not DESKTOP_DB.exists():
        raise FileNotFoundError(f"No desktop DB at {DESKTOP_DB}")

    conn = sqlite3.connect(DESKTOP_DB)
    conn.row_factory = sqlite3.Row
    try:
        counts = {}
        for table in ("accounts", "categories", "budgets", "transactions"):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

        accounts = conn.execute(
            """
            SELECT id, name, opening_balance
            FROM accounts
            ORDER BY name
            """
        ).fetchall()

        tx_rows = conn.execute(
            """
            SELECT id, sync_id, account_id, to_account_id, category_id, type, amount, occurred_at, merchant
            FROM transactions
            ORDER BY occurred_at DESC
            """
        ).fetchall()

        balances = []
        for account in accounts:
            txs = conn.execute(
                """
                SELECT account_id, to_account_id, type, amount
                FROM transactions
                WHERE account_id = ? OR to_account_id = ?
                """,
                (account["id"], account["id"]),
            ).fetchall()
            total = float(account["opening_balance"] or 0.0)
            for tx in txs:
                tx_type = (tx["type"] or "").strip().lower()
                amount = float(tx["amount"] or 0.0)
                if tx_type == "transferencia":
                    if tx["account_id"] == account["id"]:
                        total -= amount
                    elif tx["to_account_id"] == account["id"]:
                        total += amount
                elif tx_type == "ingreso":
                    total += amount
                else:
                    total -= amount
            balances.append(
                asdict(
                    BalanceRow(
                        name=account["name"],
                        opening_balance=float(account["opening_balance"] or 0.0),
                        current_balance=total,
                    )
                )
            )

        return {
            "counts": counts,
            "balances": balances,
            "transactions": [dict(row) for row in tx_rows],
        }
    finally:
        conn.close()


async def _run() -> dict[str, Any]:
    settings = get_settings()
    _delete_mobile_db(settings)
    engine = init_database()
    session_factory = build_session_factory(engine)

    auth = AuthService()
    session_manager = SessionManager()
    if not auth.tokens:
        raise RuntimeError("No hay auth_tokens.json para sincronizar contra Firebase")
    if not session_manager.has_valid_session():
        raise RuntimeError("No hay sesion valida para obtener el UID remoto")

    user_uid = session_manager.get_session_info()["user_id"]
    local_user_id = _ensure_local_user(session_factory, user_uid)
    firestore_client = FirestoreClient(settings, auth)

    initial_sync = InitialSyncService(
        session_factory=session_factory,
        firestore_client=firestore_client,
        user_uid=user_uid,
        user_id=local_user_id,
    )
    snapshot = await initial_sync.perform_snapshot_sync(mark_completed=True)

    protocol = SyncProtocol(
        session_factory=session_factory,
        firestore_client=firestore_client,
        device_id="audit-reset",
        user_uid=user_uid,
    )
    sync_result = await SimpleSyncService(protocol).sync_now(push_limit=100, pull_limit=200)

    remote = {
        "accounts": await firestore_client.get_all_accounts(user_uid),
        "categories": await firestore_client.get_all_categories(user_uid),
        "budgets": await firestore_client.get_all_budgets(user_uid),
        "transactions": await firestore_client.get_all_transactions(user_uid),
    }

    desktop = _desktop_stats()
    mobile = _mobile_stats(session_factory)

    return {
        "user_uid": user_uid,
        "paths": {
            "desktop_db": str(DESKTOP_DB),
            "mobile_db": str(settings.DB_PATH),
        },
        "snapshot_imported": snapshot,
        "sync_result": asdict(sync_result),
        "remote_counts": {key: len(value) for key, value in remote.items()},
        "desktop": desktop,
        "mobile": mobile,
    }


if __name__ == "__main__":
    result = asyncio.run(_run())
    print(json.dumps(result, indent=2, ensure_ascii=False))
