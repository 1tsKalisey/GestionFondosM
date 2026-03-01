"""
Tests para CategoryService.
"""

import pytest
from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.core.exceptions import ValidationError
from gf_mobile.persistence.models import Base, Category
from gf_mobile.services.category_service import CategoryInput, CategoryService


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
    db = SessionLocal()
    yield db
    db.close()


def test_create_duplicate_name_group_returns_existing(session):
    existing = Category(id=1, name="General", budget_group="Otros")
    session.add(existing)
    session.commit()

    service = CategoryService(session)
    created = service.create(CategoryInput(name="  general  ", budget_group=" otros "))

    assert created.id == existing.id
    assert session.query(Category).count() == 1


def test_update_rejects_duplicate_name_group(session):
    first = Category(id=1, name="Comida", budget_group="Necesidades")
    second = Category(id=2, name="Transporte", budget_group="Necesidades")
    session.add_all([first, second])
    session.commit()

    service = CategoryService(session)
    with pytest.raises(ValidationError):
        service.update(second.id, CategoryInput(name=" comida ", budget_group=" necesidades "))
