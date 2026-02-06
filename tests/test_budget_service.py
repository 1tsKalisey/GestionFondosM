"""
Tests para BudgetService
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
    Budget,
    Transaction,
    Alert,
    generate_uuid,
)
from gf_mobile.services.budget_service import BudgetService


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


class TestBudgetService:
    def test_create_budget(self, session, setup_data):
        service = BudgetService(session)
        budget = service.create_budget(
            category_id=setup_data["category_id"],
            month="2026-01",
            amount=500.0,
        )
        assert budget.id is not None
        assert budget.amount == 500.0

    def test_calculate_spent(self, session, setup_data):
        service = BudgetService(session)
        
        # Crear transacción de gasto
        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=100.0,
            currency="USD",
            occurred_at=datetime(2026, 1, 15),
        )
        session.add(tx)
        session.commit()

        spent = service.calculate_spent(setup_data["category_id"], "2026-01")
        assert spent == 100.0

    def test_check_alerts_budget_exceeded(self, session, setup_data):
        service = BudgetService(session)
        
        # Crear presupuesto
        budget = service.create_budget(
            category_id=setup_data["category_id"],
            month="2026-01",
            amount=100.0,
        )

        # Crear transacción que excede presupuesto
        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=150.0,
            currency="USD",
            occurred_at=datetime(2026, 1, 15),
        )
        session.add(tx)
        session.commit()

        alert = service.check_and_create_alerts(setup_data["category_id"], "2026-01")
        assert alert is not None
        assert alert.severity == "critical"

    def test_check_alerts_budget_warning(self, session, setup_data):
        service = BudgetService(session)
        
        budget = service.create_budget(
            category_id=setup_data["category_id"],
            month="2026-01",
            amount=100.0,
        )

        tx = Transaction(
            id=generate_uuid(),
            account_id=setup_data["account_id"],
            category_id=setup_data["category_id"],
            type="gasto",
            amount=85.0,
            currency="USD",
            occurred_at=datetime(2026, 1, 15),
        )
        session.add(tx)
        session.commit()

        alert = service.check_and_create_alerts(setup_data["category_id"], "2026-01")
        assert alert is not None
        assert alert.severity == "warning"
