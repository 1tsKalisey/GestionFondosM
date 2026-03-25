"""Common helpers to standardize SyncOutbox writes across services."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from gf_mobile.core.sync_events import resolve_event_type
from gf_mobile.persistence.models import SyncOutbox, generate_uuid


def enqueue_sync_outbox(
    session: Session,
    *,
    entity_type: str,
    operation: str,
    entity_id: str | int,
    payload: dict[str, Any],
    event_type: str | None = None,
) -> SyncOutbox:
    """Create a canonical SyncOutbox item for a local mutation."""
    outbox = SyncOutbox(
        id=generate_uuid(),
        entity_type=entity_type,
        operation=operation,
        event_type=event_type or resolve_event_type(entity_type, operation),
        entity_id=str(entity_id),
        payload=json.dumps(payload),
        created_at=datetime.now(timezone.utc),
        synced=False,
        sync_error=None,
    )
    session.add(outbox)
    return outbox


def list_pending_sync_outbox(session: Session, entity_type: str) -> list[SyncOutbox]:
    return (
        session.query(SyncOutbox)
        .filter(and_(SyncOutbox.entity_type == entity_type, SyncOutbox.synced == False))
        .order_by(SyncOutbox.created_at)
        .all()
    )


def mark_outbox_synced(session: Session, outbox_id: str) -> bool:
    outbox = session.query(SyncOutbox).filter(SyncOutbox.id == outbox_id).first()
    if not outbox:
        return False
    outbox.synced = True
    outbox.sync_error = None
    outbox.last_error = None
    return True
