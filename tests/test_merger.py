"""
Tests para MergerService
"""

import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import (
    Base,
    Account,
    Category,
    Tag,
    Transaction,
    Budget,
    generate_uuid,
)
from gf_mobile.sync.merger import MergerService


@pytest.fixture
def temp_db():
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(temp_db):
    return sessionmaker(bind=temp_db)


@pytest.fixture
def setup_data(session_factory):
    session = session_factory()
    category = Category(id=1, name="Groceries", budget_group="Necesidades")
    account = Account(
        id=generate_uuid(),
        user_id=1,
        name="Main",
        type="checking",
        currency="USD",
        opening_balance=0.0,
    )
    tag1 = Tag(id=1, name="important")
    tag2 = Tag(id=2, name="recurring")

    session.add_all([category, account, tag1, tag2])
    session.flush()
    category_id = category.id
    account_id = account.id
    session.commit()
    session.close()

    return {
        "category_id": category_id,
        "account_id": account_id,
    }


class TestMergerService:
    def test_create_transaction_event(self, session_factory, setup_data):
        merger = MergerService(session_factory)
        tx_id = generate_uuid()
        event = {
            "entity_type": "transaction",
            "operation": "create",
            "payload": {
                "id": tx_id,
                "account_id": setup_data["account_id"],
                "category_id": setup_data["category_id"],
                "type": "gasto",
                "amount": "50.0",
                "currency": "USD",
                "occurred_at": datetime(2026, 1, 1).isoformat(),
                "merchant": "Store",
                "note": "Test",
                "tag_ids": [1, 2],
            },
        }

        merger.apply_events([event])

        session = session_factory()
        tx = session.query(Transaction).filter(Transaction.id == tx_id).first()
        assert tx is not None
        assert tx.amount == 50.0
        assert {t.id for t in tx.tags} == {1, 2}
        session.close()

    def test_update_transaction_event(self, session_factory, setup_data):
        session = session_factory()
        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=10.0,
            currency="USD",
            occurred_at=datetime(2026, 1, 1),
        )
        tx.updated_at = datetime(2026, 1, 1)
        session.add(tx)
        session.commit()
        tx_id = tx.id
        session.close()

        merger = MergerService(session_factory)
        event = {
            "entity_type": "transaction",
            "operation": "update",
            "payload": {
                "id": tx_id,
                "amount": "25.0",
                "updated_at": datetime(2026, 1, 2).isoformat(),
            },
        }

        merger.apply_events([event])

        session = session_factory()
        updated = session.query(Transaction).filter(Transaction.id == tx_id).first()
        assert updated.amount == 25.0
        session.close()

    def test_delete_transaction_event(self, session_factory, setup_data):
        session = session_factory()
        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=10.0,
            currency="USD",
            occurred_at=datetime(2026, 1, 1),
        )
        session.add(tx)
        session.commit()
        tx_id = tx.id
        session.close()

        merger = MergerService(session_factory)
        event = {
            "entity_type": "transaction",
            "operation": "delete",
            "payload": {"id": tx_id},
        }

        merger.apply_events([event])

        session = session_factory()
        deleted = session.query(Transaction).filter(Transaction.id == tx_id).first()
        assert deleted is None
        session.close()

    def test_create_budget_event(self, session_factory, setup_data):
        merger = MergerService(session_factory)
        budget_id = generate_uuid()
        event = {
            "entity_type": "budget",
            "operation": "create",
            "payload": {
                "id": budget_id,
                "category_id": setup_data["category_id"],
                "month": "2026-01",
                "amount": "300.0",
            },
        }

        merger.apply_events([event])

        session = session_factory()
        budget = session.query(Budget).filter(Budget.id == budget_id).first()
        assert budget is not None
        assert budget.amount == 300.0
        session.close()
