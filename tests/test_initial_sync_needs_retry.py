from tempfile import NamedTemporaryFile

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, SyncState, User, Account, Category
from gf_mobile.sync.initial_sync import InitialSyncService


class _DummyFirestoreClient:
    async def get_all_accounts(self, user_uid):
        return []

    async def get_all_categories(self, user_uid):
        return []

    async def get_all_budgets(self, user_uid):
        return []

    async def get_all_transactions(self, user_uid):
        return []


def test_needs_initial_sync_when_marked_completed_but_no_transactions() -> None:
    with NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    user = User(name="Test", server_uid="uid-1")
    session.add(user)
    session.flush()
    local_user_id = user.id
    session.add(Account(user_id=user.id, name="Efectivo", type="efectivo", currency="EUR", opening_balance=0.0))
    session.add(Category(name="General", budget_group="Otros"))
    session.add(SyncState(key="initial_sync_completed:uid-1", value="true"))
    session.commit()
    session.close()

    service = InitialSyncService(
        session_factory=Session,
        firestore_client=_DummyFirestoreClient(),
        user_uid="uid-1",
        user_id=local_user_id,
    )
    assert service.needs_initial_sync() is True
