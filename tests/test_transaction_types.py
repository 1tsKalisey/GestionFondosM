from gf_mobile.core.transaction_types import normalize_transaction_type


def test_normalize_transaction_type_income_aliases() -> None:
    assert normalize_transaction_type("ingreso") == "ingreso"
    assert normalize_transaction_type("income") == "ingreso"
    assert normalize_transaction_type("credit") == "ingreso"


def test_normalize_transaction_type_expense_aliases() -> None:
    assert normalize_transaction_type("gasto") == "gasto"
    assert normalize_transaction_type("expense") == "gasto"
    assert normalize_transaction_type("debit") == "gasto"


def test_normalize_transaction_type_transfer_aliases() -> None:
    assert normalize_transaction_type("transfer") == "transferencia"
    assert normalize_transaction_type("transferencia") == "transferencia"


def test_normalize_transaction_type_unknown_passthrough() -> None:
    assert normalize_transaction_type("otro_tipo") == "otro_tipo"
    assert normalize_transaction_type("") == ""
    assert normalize_transaction_type(None) == ""
