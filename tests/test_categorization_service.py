"""
Tests para CategorizationService
"""

import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import (
    Base,
    Category,
    Transaction,
    Account,
    User,
    generate_uuid,
)
from gf_mobile.services.categorization_service import CategorizationService


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
    user = User(name="Test User")
    groceries = Category(id=1, name="Groceries", budget_group="Necessities")
    restaurant = Category(id=2, name="Restaurants", budget_group="Food")
    account = Account(
        id=generate_uuid(),
        user_id=1,
        name="Main",
        type="checking",
        currency="USD",
        opening_balance=0.0,
    )
    session.add_all([user, groceries, restaurant, account])
    session.flush()
    session.commit()
    return {
        "user_id": user.id,
        "account_id": account.id,
        "groceries_id": groceries.id,
        "restaurant_id": restaurant.id,
    }


class TestCategorizationService:
    def test_categorize_with_user_input(self, session, setup_data):
        """Usuario proporciona categoría, servicio aprende."""
        service = CategorizationService(session)
        cat_id, confidence = service.categorize_transaction(
            merchant="Whole Foods Market",
            amount=150.0,
            category_id=setup_data["groceries_id"],
        )
        assert cat_id == setup_data["groceries_id"]
        assert confidence >= 0.7

    def test_learn_from_transaction(self, session, setup_data):
        """Aprende regla a partir de transacción categorizada."""
        service = CategorizationService(session)
        rule = service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Trader Joe's",
            category_id=setup_data["groceries_id"],
        )
        assert rule.merchant_keyword == "trader joe's"
        assert rule.confidence == 0.6
        assert rule.user_defined is False

    def test_reuse_learned_rule(self, session, setup_data):
        """Si regla existe, reutiliza con mayor confianza."""
        service = CategorizationService(session)

        # Primera vez aprende
        rule1 = service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Starbucks",
            category_id=setup_data["restaurant_id"],
        )
        conf1 = rule1.confidence

        # Segunda vez reutiliza y aumenta confianza
        rule2 = service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Starbucks",
            category_id=setup_data["restaurant_id"],
        )
        assert rule2.confidence > conf1

    def test_get_category_suggestion(self, session, setup_data):
        """Obtiene sugerencia de categoría para merchant."""
        service = CategorizationService(session)
        service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Walgreens",
            category_id=setup_data["restaurant_id"],
        )
        suggestion = service.get_category_suggestion(
            merchant="Walgreens", amount=25.0
        )
        assert suggestion is not None
        assert suggestion["category_id"] == setup_data["restaurant_id"]
        assert suggestion["confidence"] == 0.6

    def test_get_rules_by_category(self, session, setup_data):
        """Obtiene todas las reglas para una categoría."""
        service = CategorizationService(session)
        service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Whole Foods",
            category_id=setup_data["groceries_id"],
        )
        service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Trader Joe's",
            category_id=setup_data["groceries_id"],
        )
        rules = service.get_rules_by_category(setup_data["groceries_id"])
        assert len(rules) == 2

    def test_update_rule_confidence(self, session, setup_data):
        """Actualiza la confianza de una regla."""
        service = CategorizationService(session)
        rule = service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Amazon",
            category_id=setup_data["restaurant_id"],
        )
        updated = service.update_rule_confidence(rule.id, 0.95)
        assert updated.confidence == 0.95

    def test_invalid_confidence(self, session, setup_data):
        """Rechaza confianza fuera de rango."""
        service = CategorizationService(session)
        rule = service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="Test",
            category_id=setup_data["groceries_id"],
        )
        with pytest.raises(ValueError):
            service.update_rule_confidence(rule.id, 1.5)

    def test_list_pending_sync(self, session, setup_data):
        """Retorna reglas pendientes de sincronización."""
        service = CategorizationService(session)
        service.learn_from_transaction(
            transaction_id=generate_uuid(),
            merchant="CVS",
            category_id=setup_data["restaurant_id"],
        )
        pending = service.list_pending_sync()
        assert len(pending) == 1
        assert pending[0]["operation"] == "create"
