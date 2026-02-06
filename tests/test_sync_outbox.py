from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, User, Account, Category, Transaction, SyncOutbox
from gf_mobile.services.transaction_service import TransactionService


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_transaction_enqueue_outbox() -> None:
    session = build_session()
    user = User(name="Test")
    session.add(user)
    session.flush()
    account = Account(user_id=user.id, name="Cash", type="efectivo", currency="USD", opening_balance=0.0)
    category = Category(name="Food", budget_group="Otros")
    session.add_all([account, category])
    session.commit()

    service = TransactionService(session, user_id=str(user.id))
    tx = service.create(
        account_id=account.id,
        type_="gasto",
        amount=10.0,
        category_id=category.id,
        currency="USD",
        occurred_at=datetime.utcnow(),
        merchant="Store",
        note="Test",
    )

    outbox = session.query(SyncOutbox).filter(SyncOutbox.entity_id == tx.id).first()
    assert outbox is not None
    assert outbox.event_type == "txn_created"
