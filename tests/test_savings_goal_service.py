"""
Tests para SavingsGoalService
"""

import pytest
from datetime import datetime, timedelta, timezone
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, SavingsGoal, Category, User
from gf_mobile.services.savings_goal_service import SavingsGoalService


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
    category = Category(id=1, name="Vacation", budget_group="Discretionary")
    session.add_all([user, category])
    session.flush()
    session.commit()
    return {"user_id": user.id, "category_id": category.id}


class TestSavingsGoalService:
    def test_create_goal(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="Vacation Fund",
            target_amount=5000.0,
            current_amount=0.0,
            category_id=setup_data["category_id"],
        )
        assert goal.id is not None
        assert goal.name == "Vacation Fund"
        assert goal.target_amount == 5000.0
        assert goal.achieved is False

    def test_update_goal(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="Vacation Fund",
            target_amount=5000.0,
        )
        updated = service.update_goal(
            goal.id,
            name="Summer Vacation",
            target_amount=6000.0,
        )
        assert updated.name == "Summer Vacation"
        assert updated.target_amount == 6000.0

    def test_add_contribution(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="Vacation Fund",
            target_amount=5000.0,
            current_amount=0.0,
        )
        updated = service.add_contribution(goal.id, 1500.0)
        assert updated.current_amount == 1500.0

    def test_contribution_marks_achieved(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="Small Goal",
            target_amount=100.0,
            current_amount=50.0,
        )
        updated = service.add_contribution(goal.id, 60.0)
        assert updated.current_amount == 110.0
        assert updated.achieved is True

    def test_get_progress(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="Vacation Fund",
            target_amount=5000.0,
            current_amount=1500.0,
            deadline=datetime.now(timezone.utc) + timedelta(days=180),
        )
        progress = service.get_progress(goal.id)
        assert progress["percentage"] == 30.0
        assert progress["remaining"] == 3500.0
        assert progress["achieved"] is False

    def test_list_goals_filter_by_achieved(self, session, setup_data):
        service = SavingsGoalService(session)
        service.create_goal(user_id=setup_data["user_id"], name="Goal 1", target_amount=1000.0, current_amount=1000.0)
        service.create_goal(user_id=setup_data["user_id"], name="Goal 2", target_amount=2000.0, current_amount=500.0)
        
        achieved = service.list_goals(achieved=True)
        not_achieved = service.list_goals(achieved=False)
        
        assert len(achieved) == 1
        assert len(not_achieved) == 1

    def test_delete_goal(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(
            user_id=setup_data["user_id"],
            name="To Delete",
            target_amount=1000.0,
        )
        deleted = service.delete_goal(goal.id)
        assert deleted is True
        
        # Verify actually deleted
        retrieved = service.get_goal(goal.id)
        assert retrieved is None

    def test_invalid_target_amount(self, session, setup_data):
        service = SavingsGoalService(session)
        with pytest.raises(ValueError):
            service.create_goal(user_id=setup_data["user_id"], name="Bad Goal", target_amount=-100.0)

    def test_invalid_current_amount(self, session, setup_data):
        service = SavingsGoalService(session)
        with pytest.raises(ValueError):
            service.create_goal(user_id=setup_data["user_id"], name="Bad Goal", target_amount=1000.0, current_amount=-50.0)

    def test_negative_contribution(self, session, setup_data):
        service = SavingsGoalService(session)
        goal = service.create_goal(user_id=setup_data["user_id"], name="Goal", target_amount=1000.0)
        with pytest.raises(ValueError):
            service.add_contribution(goal.id, -100.0)
