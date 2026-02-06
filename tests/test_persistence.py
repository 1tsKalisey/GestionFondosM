"""
Tests para persistencia SQLite y modelos
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.db import init_database, get_session
from gf_mobile.persistence.models import (
    Base,
    User,
    Account,
    Category,
    SubCategory,
    Transaction,
    RecurringTransaction,
    Budget,
    generate_uuid,
)


@pytest.fixture
def temp_db():
    """Crear BD temporal para tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_url = f"sqlite:///{db_path}"

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)

        SessionFactory = sessionmaker(bind=engine)
        yield SessionFactory, engine

        engine.dispose()


class TestModels:
    """Tests para modelos SQLAlchemy"""

    def test_user_creation(self, temp_db):
        """Crear usuario"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        user = User(name="Test User")
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.name == "Test User"

    def test_account_uuid(self, temp_db):
        """Verificar que Account usa UUID"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        user = User(name="Test User")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            name="Test Account",
            type="checking",
            currency="USD",
            opening_balance=1000.0,
        )
        session.add(account)
        session.commit()

        # Verificar que el ID es UUID string
        assert account.id is not None
        assert isinstance(account.id, str)
        assert len(account.id) == 36  # UUID string length

    def test_transaction_creation(self, temp_db):
        """Crear transacción"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        # Setup
        user = User(name="User")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            name="Account",
            type="checking",
            currency="USD",
            opening_balance=0,
        )
        session.add(account)
        session.commit()

        category = Category(name="Food", budget_group="Necesidades")
        session.add(category)
        session.commit()

        # Crear transacción
        txn = Transaction(
            account_id=account.id,
            category_id=category.id,
            type="gasto",
            amount=50.0,
            currency="USD",
            occurred_at=datetime.now(),
            merchant="Supermarket",
            note="Groceries",
        )
        session.add(txn)
        session.commit()

        assert txn.id is not None
        assert txn.amount == 50.0
        assert txn.synced is False

    def test_transaction_uuid_generation(self, temp_db):
        """Verificar generación automática de UUID para transacciones"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        user = User(name="User")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, name="Account", type="checking", currency="USD"
        )
        session.add(account)
        session.commit()

        category = Category(name="Food", budget_group="Necesidades")
        session.add(category)
        session.commit()

        # Crear dos transacciones; deben tener IDs diferentes
        txn1 = Transaction(
            account_id=account.id,
            category_id=category.id,
            type="gasto",
            amount=10.0,
            currency="USD",
            occurred_at=datetime.now(),
        )
        txn2 = Transaction(
            account_id=account.id,
            category_id=category.id,
            type="gasto",
            amount=20.0,
            currency="USD",
            occurred_at=datetime.now(),
        )
        session.add(txn1)
        session.add(txn2)
        session.commit()

        assert txn1.id != txn2.id

    def test_recurring_transaction(self, temp_db):
        """Crear transacción recurrente"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        user = User(name="User")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, name="Account", type="checking", currency="USD"
        )
        session.add(account)
        session.commit()

        category = Category(name="Utilities", budget_group="Necesidades")
        session.add(category)
        session.commit()

        recurring = RecurringTransaction(
            name="Monthly Rent",
            type="gasto",
            amount=1000.0,
            currency="USD",
            category_id=category.id,
            account_id=account.id,
            frequency="monthly",
            start_date=datetime.now(),
            auto_generate=True,
        )
        session.add(recurring)
        session.commit()

        assert recurring.id is not None
        assert recurring.frequency == "monthly"
        assert recurring.auto_generate is True

    def test_budget_creation(self, temp_db):
        """Crear presupuesto"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        category = Category(name="Food", budget_group="Necesidades")
        session.add(category)
        session.commit()

        budget = Budget(category_id=category.id, month="2025-02", amount=500.0)
        session.add(budget)
        session.commit()

        assert budget.id is not None
        assert budget.month == "2025-02"
        assert budget.amount == 500.0

    def test_budget_unique_constraint(self, temp_db):
        """Verificar constraint único en budget (category_id, month)"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        category = Category(name="Food", budget_group="Necesidades")
        session.add(category)
        session.commit()

        budget1 = Budget(category_id=category.id, month="2025-02", amount=500.0)
        session.add(budget1)
        session.commit()

        # Intentar crear presupuesto duplicado
        budget2 = Budget(category_id=category.id, month="2025-02", amount=600.0)
        session.add(budget2)

        with pytest.raises(Exception):  # IntegrityError
            session.commit()

    def test_sync_outbox_integration(self, temp_db):
        """Verificar flujo de outbox para transacciones"""
        SessionFactory, _ = temp_db
        session = SessionFactory()

        user = User(name="User")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, name="Account", type="checking", currency="USD"
        )
        session.add(account)
        session.commit()

        category = Category(name="Food", budget_group="Necesidades")
        session.add(category)
        session.commit()

        txn = Transaction(
            account_id=account.id,
            category_id=category.id,
            type="gasto",
            amount=50.0,
            currency="USD",
            occurred_at=datetime.now(),
        )
        session.add(txn)
        session.commit()

        # Verificar que transacción está por sincronizar
        assert txn.synced is False
        assert txn.conflict_resolved is False

        # Simular sincronización
        txn.synced = True
        session.commit()

        assert txn.synced is True
