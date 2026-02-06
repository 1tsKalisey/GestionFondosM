"""
Tests para RecurringService
"""

import json
import pytest
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, Account, Category, RecurringTransaction, Transaction, SyncOutbox, generate_uuid
from gf_mobile.services.recurring_service import RecurringService


@pytest.fixture
def temp_db():
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(temp_db):
    SessionLocal = sessionmaker(bind=temp_db)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def setup_data(session):
    category = Category(id=1, name="Groceries", budget_group="Necesidades")
    account = Account(
        id=generate_uuid(),
        user_id=1,
        name="Main",
        type="checking",
        currency="USD",
        opening_balance=0.0,
    )
    session.add_all([category, account])
    session.commit()
    return {"category_id": category.id, "account_id": account.id}


class TestRecurringService:
    def test_create_recurring(self, session, setup_data):
        service = RecurringService(session)
        start = datetime.utcnow()
        recurring = service.create(
            name="Rent",
            type_="gasto",
            amount=1000.0,
            currency="USD",
            category_id=setup_data["category_id"],
            account_id=setup_data["account_id"],
            frequency="monthly",
            start_date=start,
            auto_generate=True,
        )

        assert recurring.id is not None
        outbox = session.query(SyncOutbox).filter(SyncOutbox.entity_type == "recurring").first()
        assert outbox is not None

    def test_generate_due_transactions(self, session, setup_data):
        service = RecurringService(session)
        past = datetime.utcnow() - timedelta(days=1)
        recurring = RecurringTransaction(
            name="Gym",
            type="gasto",
            amount=50.0,
            currency="USD",
            category_id=setup_data["category_id"],
            account_id=setup_data["account_id"],
            frequency="monthly",
            start_date=past,
            auto_generate=True,
            next_run=past,
        )
        session.add(recurring)
        session.commit()

        created = service.generate_due_transactions(as_of=datetime.utcnow())
        assert created == 1

        tx = session.query(Transaction).filter(Transaction.recurring_id == recurring.id).first()
        assert tx is not None

        updated = session.query(RecurringTransaction).filter(RecurringTransaction.id == recurring.id).first()
        assert updated.next_run > past

    def test_generate_skips_existing(self, session, setup_data):
        service = RecurringService(session)
        past = datetime.utcnow() - timedelta(days=1)
        recurring = RecurringTransaction(
            name="Netflix",
            type="gasto",
            amount=15.0,
            currency="USD",
            category_id=setup_data["category_id"],
            account_id=setup_data["account_id"],
            frequency="monthly",
            start_date=past,
            auto_generate=True,
            next_run=past,
        )
        session.add(recurring)
        session.commit()

        # Crear transacción existente
        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=15.0,
            currency="USD",
            occurred_at=past,
            recurring_id=recurring.id,
        )
        session.add(tx)
        session.commit()

        created = service.generate_due_transactions(as_of=datetime.utcnow())
        assert created == 0

    def test_compute_next_run_monthly_interval(self, session):
        service = RecurringService(session)
        last = datetime(2026, 1, 1)
        next_run = service.compute_next_run(last, "monthly:2")
        assert next_run.month == 3
