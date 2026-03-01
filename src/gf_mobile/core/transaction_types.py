"""
Helpers para normalizar tipos de transaccion entre fuentes.
"""

from __future__ import annotations


def normalize_transaction_type(value: str | None) -> str:
    """
    Normaliza variantes de tipo a los valores canónicos de la app:
    - ingreso
    - gasto
    - transferencia
    """
    raw = (value or "").strip().lower()
    if not raw:
        return raw

    aliases = {
        "ingreso": "ingreso",
        "income": "ingreso",
        "credit": "ingreso",
        "deposit": "ingreso",
        "gasto": "gasto",
        "expense": "gasto",
        "debit": "gasto",
        "withdrawal": "gasto",
        "transferencia": "transferencia",
        "transfer": "transferencia",
    }
    return aliases.get(raw, raw)
