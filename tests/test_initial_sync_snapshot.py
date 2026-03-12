import asyncio
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tempfile import NamedTemporaryFile

from gf_mobile.persistence.models import Base, User, Account, Budget, Category, Transaction
from gf_mobile.sync.initial_sync import InitialSyncService


class _FakeFirestoreClient:
    def __init__(self, *, accounts, categories, budgets, transactions):
        self._accounts = accounts
        self._categories = categories
        self._budgets = budgets
        self._transactions = transactions

    async def get_all_accounts(self, user_uid):
        return list(self._accounts)

    async def get_all_categories(self, user_uid):
        return list(self._categories)

    async def get_all_budgets(self, user_uid):
        return list(self._budgets)

    async def get_all_transactions(self, user_uid):
        return list(self._transactions)


def _build_session_factory():
    db_file = NamedTemporaryFile(suffix=".db", delete=False)
    db_file.close()
    engine = create_engine(f"sqlite:///{db_file.name}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_snapshot_sync_imports_desktop_documents_and_maps_remote_ids() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    session.add(User(name="Test", server_uid="uid-1"))
    session.commit()

    firestore_client = _FakeFirestoreClient(
        accounts=[
            {
                "id": 1,
                "sync_id": "acc-sync-1",
                "name": "Cuenta ahorro",
                "type": "checking",
                "currency": "EUR",
                "opening_balance": 1250.5,
            },
            {
                "id": 2,
                "sync_id": "acc-sync-2",
                "name": "Cuenta principal",
                "type": "checking",
                "currency": "EUR",
                "opening_balance": 800,
            },
        ],
        categories=[
            {
                "id": 10,
                "sync_id": "cat-sync-10",
                "name": "Comida",
                "budget_group": "Necesidades",
            }
        ],
        budgets=[
            {
                "id": "budget-1",
                "category_id": "cat-sync-10",
                "month": "2026-03",
                "amount": 300,
            }
        ],
        transactions=[
            {
                "id": "tx-doc-1",
                "sync_id": "tx-sync-1",
                "account_id": "acc-sync-1",
                "to_account_id": "acc-sync-2",
                "category_id": "cat-sync-10",
                "type": "gasto",
                "amount": 42.75,
                "currency": "EUR",
                "occurred_at": "2026-03-10T10:00:00Z",
                "merchant": "Mercado",
                "note": "Compra semanal",
            }
        ],
    )
    service = InitialSyncService(
        session_factory=session_factory,
        firestore_client=firestore_client,
        user_uid="uid-1",
        user_id=None,
    )

    async def _run_import() -> dict[str, int]:
        return {
            "accounts": await service._sync_accounts(session),
            "categories": await service._sync_categories(session),
            "budgets": await service._sync_budgets(session),
        }

    imported = asyncio.run(_run_import())
    session.commit()

    assert imported == {
        "accounts": 2,
        "categories": 1,
        "budgets": 1,
    }

    session.close()


def test_snapshot_sync_updates_existing_rows_on_subsequent_runs() -> None:
    session_factory = _build_session_factory()
    session = session_factory()
    user = User(name="Test", server_uid="uid-1")
    session.add(user)
    session.flush()
    account = Account(user_id=user.id, name="Vieja", type="cash", currency="USD", opening_balance=0, server_id="1")
    category = Category(name="Comida", budget_group="Otros", sync_id="10")
    session.add_all([account, category])
    session.flush()
    budget = Budget(id="budget-1", category_id=category.id, month="2026-03", amount=50, synced=False)
    transaction = Transaction(
        id="tx-1",
        account_id=account.id,
        category_id=category.id,
        type="gasto",
        amount=10,
        currency="USD",
        occurred_at=service_dt("2026-03-01T10:00:00Z"),
        merchant="Viejo",
        note="Antes",
        synced=False,
    )
    session.add_all([budget, transaction])
    session.commit()
    session.close()

    firestore_client = _FakeFirestoreClient(
        accounts=[{"id": 1, "name": "Nueva", "type": "checking", "currency": "EUR", "opening_balance": 900}],
        categories=[{"id": 10, "name": "Comida", "budget_group": "Necesidades"}],
        budgets=[{"id": "budget-1", "category_id": 10, "month": "2026-03", "amount": 275}],
        transactions=[
            {
                "id": "tx-1",
                "account_id": 1,
                "category_id": 10,
                "type": "gasto",
                "amount": 99,
                "currency": "EUR",
                "occurred_at": "2026-03-15T11:30:00Z",
                "merchant": "Nuevo",
                "note": "Despues",
            }
        ],
    )
    service = InitialSyncService(
        session_factory=session_factory,
        firestore_client=firestore_client,
        user_uid="uid-1",
        user_id=None,
    )

    imported = asyncio.run(service.perform_snapshot_sync(mark_completed=False))

    assert imported == {
        "accounts": 0,
        "categories": 0,
        "budgets": 0,
        "transactions": 0,
    }

    session = session_factory()
    account = session.query(Account).one()
    category = session.query(Category).one()
    budget = session.query(Budget).one()
    transaction = session.query(Transaction).one()
    assert account.name == "Nueva"
    assert account.currency == "EUR"
    assert category.budget_group == "Necesidades"
    assert budget.amount == 275
    assert transaction.amount == 99
    assert transaction.note == "Despues"
    session.close()


def service_dt(value: str):
    return InitialSyncService._parse_remote_datetime(value)
