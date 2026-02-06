"""
Tests para SyncProtocol
"""

import json
import pytest
from datetime import datetime
from tempfile import NamedTemporaryFile
from unittest.mock import AsyncMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gf_mobile.persistence.models import Base, SyncOutbox, generate_uuid
from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.sync.firestore_client import FirestoreClient


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
def firestore_client_mock():
    client = AsyncMock(spec=FirestoreClient)
    client.create_event = AsyncMock(return_value="evt-1")
    client.fetch_events_since = AsyncMock(return_value=([{"id": "evt-1"}], None))
    return client


@pytest.fixture
def protocol(session_factory, firestore_client_mock):
    return SyncProtocol(
        session_factory=session_factory,
        firestore_client=firestore_client_mock,
        device_id="device-1",
        user_uid="user-uid-1",
    )


class TestSyncProtocol:
    """Tests básicos de SyncProtocol."""

    @pytest.mark.asyncio
    async def test_push_outbox_marks_synced(self, session_factory, protocol):
        session = session_factory()
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type="transaction",
            operation="create",
            entity_id="tx-1",
            payload=json.dumps({"amount": "10.0"}),
            created_at=datetime.utcnow(),
            synced=False,
        )
        session.add(outbox)
        session.commit()
        outbox_id = outbox.id
        session.close()

        pushed = await protocol.push_outbox()
        assert pushed == 1

        session = session_factory()
        updated = session.query(SyncOutbox).filter(SyncOutbox.id == outbox_id).first()
        assert updated.synced is True
        assert updated.sync_error is None
        session.close()

    @pytest.mark.asyncio
    async def test_push_outbox_sets_error_on_failure(self, session_factory, firestore_client_mock):
        firestore_client_mock.create_event = AsyncMock(side_effect=Exception("fail"))
        protocol = SyncProtocol(
            session_factory=session_factory,
            firestore_client=firestore_client_mock,
            device_id="device-1",
            user_uid="user-uid-1",
        )

        session = session_factory()
        outbox = SyncOutbox(
            id=generate_uuid(),
            entity_type="transaction",
            operation="create",
            entity_id="tx-2",
            payload=json.dumps({"amount": "20.0"}),
            created_at=datetime.utcnow(),
            synced=False,
        )
        session.add(outbox)
        session.commit()
        outbox_id = outbox.id
        session.close()

        pushed = await protocol.push_outbox()
        assert pushed == 0

        session = session_factory()
        updated = session.query(SyncOutbox).filter(SyncOutbox.id == outbox_id).first()
        assert updated.synced is False
        assert updated.sync_error is not None
        session.close()

    @pytest.mark.asyncio
    async def test_pull_events_returns_list(self, protocol):
        events, token = await protocol.pull_events(since_timestamp=None)
        assert isinstance(events, list)
        assert events[0]["id"] == "evt-1"
        assert token is None
