from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from gf_mobile.core.auth import AuthService
from gf_mobile.core.config import get_settings
from gf_mobile.core.session_manager import SessionManager
from gf_mobile.sync.firestore_client import FirestoreClient


DESKTOP_DB = Path.home() / ".gestionfondos" / "gestionfondos.db"


def _iso(value):
    return value if value else None


async def _run() -> None:
    if not DESKTOP_DB.exists():
        raise FileNotFoundError(f"No existe la base de escritorio: {DESKTOP_DB}")

    auth = AuthService()
    session_manager = SessionManager()
    if not auth.tokens:
        raise RuntimeError("No hay auth_tokens.json para publicar snapshot")
    if not session_manager.has_valid_session():
        raise RuntimeError("No hay sesión válida para obtener el UID remoto")

    user_uid = session_manager.get_session_info()["user_id"]
    client = FirestoreClient(get_settings(), auth)

    conn = sqlite3.connect(DESKTOP_DB)
    conn.row_factory = sqlite3.Row
    try:
        accounts = conn.execute(
            "SELECT id, sync_id, name, type, currency, opening_balance, created_at FROM accounts"
        ).fetchall()
        categories = conn.execute(
            "SELECT id, sync_id, name, budget_group, created_at FROM categories"
        ).fetchall()
        budgets = conn.execute(
            """
            SELECT b.id, c.sync_id AS category_sync_id, b.category_id, b.month, b.amount, b.created_at
            FROM budgets b
            LEFT JOIN categories c ON c.id = b.category_id
            """
        ).fetchall()
        transactions = conn.execute(
            """
            SELECT
                t.id,
                t.sync_id,
                src.sync_id AS account_sync_id,
                dst.sync_id AS to_account_sync_id,
                c.sync_id AS category_sync_id,
                t.account_id,
                t.to_account_id,
                t.category_id,
                t.type,
                t.amount,
                t.currency,
                t.occurred_at,
                t.merchant,
                t.note,
                t.created_at
            FROM transactions t
            LEFT JOIN accounts src ON src.id = t.account_id
            LEFT JOIN accounts dst ON dst.id = t.to_account_id
            LEFT JOIN categories c ON c.id = t.category_id
            """
        ).fetchall()

        for row in accounts:
            await client.upsert_account(
                user_uid=user_uid,
                account_id=row["id"],
                account_data={
                    "id": row["id"],
                    "sync_id": row["sync_id"],
                    "name": row["name"],
                    "type": row["type"],
                    "currency": row["currency"],
                    "opening_balance": float(row["opening_balance"] or 0.0),
                    "created_at": _iso(row["created_at"]),
                },
            )

        for row in categories:
            await client.upsert_category(
                user_uid=user_uid,
                category_id=row["id"],
                category_data={
                    "id": row["id"],
                    "sync_id": row["sync_id"],
                    "name": row["name"],
                    "budget_group": row["budget_group"],
                    "created_at": _iso(row["created_at"]),
                },
            )

        for row in budgets:
            await client.upsert_budget(
                user_uid=user_uid,
                budget_id=row["id"],
                budget_data={
                    "id": row["id"],
                    "category_id": row["category_sync_id"] or row["category_id"],
                    "month": row["month"],
                    "amount": float(row["amount"] or 0.0),
                    "created_at": _iso(row["created_at"]),
                },
            )

        for row in transactions:
            await client.upsert_transaction(
                user_uid=user_uid,
                transaction_id=row["id"],
                transaction_data={
                    "id": row["id"],
                    "sync_id": row["sync_id"],
                    "account_id": row["account_sync_id"] or row["account_id"],
                    "to_account_id": row["to_account_sync_id"] or row["to_account_id"],
                    "category_id": row["category_sync_id"] or row["category_id"],
                    "type": row["type"],
                    "amount": float(row["amount"] or 0.0),
                    "currency": row["currency"] or "EUR",
                    "occurred_at": _iso(row["occurred_at"]),
                    "merchant": row["merchant"],
                    "note": row["note"],
                    "created_at": _iso(row["created_at"]),
                },
            )
    finally:
        conn.close()

    print(
        json.dumps(
            {
                "user_uid": user_uid,
                "published": {
                    "accounts": len(accounts),
                    "categories": len(categories),
                    "budgets": len(budgets),
                    "transactions": len(transactions),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    asyncio.run(_run())
