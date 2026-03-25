"""
Tests para CategoryService.
"""

import json
from tempfile import NamedTemporaryFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.core.exceptions import ValidationError
from gf_mobile.persistence.models import Base, Category, SyncOutbox
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


def test_create_duplicate_name_returns_existing(session):
    existing = Category(name="General", budget_group="Otros")
    session.add(existing)
    session.commit()

    service = CategoryService(session)
    created = service.create(CategoryInput(name="  general  ", budget_group=" necesidades "))

    assert created.id == existing.id
    assert session.query(Category).count() == 1


def test_update_rejects_duplicate_name(session):
    first = Category(name="Comida", budget_group="Necesidades")
    second = Category(name="Transporte", budget_group="Necesidades")
    session.add_all([first, second])
    session.commit()

    service = CategoryService(session)
    with pytest.raises(ValidationError):
        service.update(second.id, CategoryInput(name=" comida ", budget_group=" ocio "))


def test_create_generates_valid_sync_outbox(session):
    service = CategoryService(session)

    category = service.create(CategoryInput(name="Viajes", budget_group="Ocio/Deseos"))

    outbox = session.query(SyncOutbox).filter(SyncOutbox.entity_id == str(category.id)).first()

    assert outbox is not None
    assert outbox.entity_type == "category"
    assert outbox.operation == "create"
    assert outbox.event_type == "category_created"
    payload = json.loads(outbox.payload)
    assert payload["id"] == category.id
    assert payload["name"] == "Viajes"
    assert payload["budget_group"] == "Ocio/Deseos"


def test_update_generates_valid_sync_outbox(session):
    category = Category(name="Casa", budget_group="Necesidades")
    session.add(category)
    session.commit()

    service = CategoryService(session)
    service.update(category.id, CategoryInput(name="Hogar", budget_group="Necesidades"))

    outbox = (
        session.query(SyncOutbox)
        .filter(SyncOutbox.entity_id == str(category.id), SyncOutbox.operation == "update")
        .first()
    )

    assert outbox is not None
    assert outbox.event_type == "category_updated"
    payload = json.loads(outbox.payload)
    assert payload["name"] == "Hogar"


def test_delete_generates_valid_sync_outbox(session):
    category = Category(name="Salud", budget_group="Necesidades")
    session.add(category)
    session.commit()

    service = CategoryService(session)
    deleted = service.delete(category.id)

    outbox = (
        session.query(SyncOutbox)
        .filter(SyncOutbox.entity_id == str(category.id), SyncOutbox.operation == "delete")
        .first()
    )

    assert deleted is True
    assert outbox is not None
    assert outbox.event_type == "category_deleted"
    payload = json.loads(outbox.payload)
    assert payload["name"] == "Salud"
