"""
SyncProtocol

Orquesta sincronización push/pull entre SQLite y Firestore.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from gf_mobile.core.exceptions import SyncError
from gf_mobile.persistence.models import SyncOutbox, SyncState, AppliedEvent
from gf_mobile.sync.firestore_client import FirestoreClient
from gf_mobile.sync.merger import MergerService


class SyncProtocol:
    """Protocolo de sincronización (push/pull)."""

    def __init__(
        self,
        session_factory,
        firestore_client: FirestoreClient,
        device_id: str,
        user_uid: str,
    ) -> None:
        self.session_factory = session_factory
        self.firestore_client = firestore_client
        self.device_id = device_id
        self.user_uid = user_uid

    def _get_state(self, session: Session, key: str) -> Optional[str]:
        item = session.query(SyncState).filter(SyncState.key == key).first()
        return item.value if item else None

    def _set_state(self, session: Session, key: str, value: Optional[str]) -> None:
        item = session.query(SyncState).filter(SyncState.key == key).first()
        if not item:
            item = SyncState(key=key, value=value)
            session.add(item)
        else:
            item.value = value

    async def push_outbox(self, limit: int = 50) -> int:
        """Envía cambios locales pendientes a Firestore."""
        session = self.session_factory()
        pushed = 0
        try:
            outbox_items = (
                session.query(SyncOutbox)
                .filter(
                    SyncOutbox.synced == False,
                    (SyncOutbox.next_attempt_at == None)
                    | (SyncOutbox.next_attempt_at <= datetime.utcnow()),
                )
                .order_by(SyncOutbox.created_at)
                .limit(limit)
                .all()
            )

            for item in outbox_items:
                payload = json.loads(item.payload)
                try:
                    await self.firestore_client.create_event(
                        user_uid=self.user_uid,
                        device_id=self.device_id,
                        event_id=item.id,
                        event_type=item.event_type or "txn_updated",
                        entity_id=item.entity_id,
                        payload=payload,
                    )
                    item.synced = True
                    item.sync_error = None
                    item.last_error = None
                    pushed += 1
                except Exception as e:
                    item.sync_error = str(e)
                    item.last_error = str(e)
                    item.retry_count = (item.retry_count or 0) + 1
                    delay = min(3600, 2 ** min(item.retry_count, 10))
                    item.next_attempt_at = datetime.utcnow() + timedelta(seconds=delay)

            self._set_state(
                session,
                "last_push_timestamp",
                datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            )

            session.commit()
            return pushed
        except Exception as e:
            session.rollback()
            raise SyncError(f"Error en push_outbox: {str(e)}")
        finally:
            session.close()

    async def pull_events(
        self,
        since_timestamp: Optional[str] = None,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Descarga eventos desde Firestore (sin aplicar merge)."""
        try:
            return await self.firestore_client.fetch_events_since(
                user_uid=self.user_uid,
                since_timestamp=since_timestamp,
                page_size=page_size,
            )
        except Exception as e:
            raise SyncError(f"Error en pull_events: {str(e)}")

    def get_last_pull_timestamp(self) -> Optional[str]:
        session = self.session_factory()
        try:
            return self._get_state(session, "last_applied_at")
        finally:
            session.close()

    def update_last_pull_timestamp(self, timestamp: str) -> None:
        session = self.session_factory()
        try:
            self._set_state(session, "last_applied_at", timestamp)
            session.commit()
        finally:
            session.close()

    async def pull_and_apply(self, page_size: int = 50) -> int:
        """Descarga y aplica eventos remotos."""
        session = self.session_factory()
        try:
            merger = MergerService(self.session_factory)
            last_applied_at = self._get_state(session, "last_applied_at")
            last_applied_event_id = self._get_state(session, "last_applied_event_id")
            events, _ = await self.firestore_client.fetch_events_since(
                user_uid=self.user_uid,
                since_timestamp=last_applied_at,
                page_size=page_size,
            )
            applied = 0
            for event in events:
                event_id = event.get("id")
                if not event_id:
                    continue
                if session.get(AppliedEvent, event_id):
                    continue
                if event.get("originDeviceId") == self.device_id:
                    session.add(AppliedEvent(event_id=event_id))
                    last_applied_at = event.get("createdAt") or last_applied_at
                    last_applied_event_id = event_id
                    continue
                merger.apply_event(session, event)
                session.add(AppliedEvent(event_id=event_id))
                last_applied_at = event.get("createdAt") or last_applied_at
                last_applied_event_id = event_id
                applied += 1

            self._set_state(session, "last_applied_at", last_applied_at)
            self._set_state(session, "last_applied_event_id", last_applied_event_id)
            session.commit()
            return applied
        except Exception as e:
            session.rollback()
            raise SyncError(f"Error en pull_and_apply: {str(e)}")
        finally:
            session.close()
