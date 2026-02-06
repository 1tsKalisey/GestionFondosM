"""
FirestoreClient

Cliente REST para Firestore.
"""

from __future__ import annotations

import aiohttp
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from gf_mobile.core.exceptions import NetworkError
from gf_mobile.core.config import Settings
from gf_mobile.core.auth import AuthService


class FirestoreClient:
    """Cliente REST para Firestore (sin SDK)."""

    def __init__(
        self,
        settings: Settings,
        auth_service: AuthService,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.settings = settings
        self.auth_service = auth_service
        self._session = session

    @property
    def _base_url(self) -> str:
        return f"{self.settings.FIRESTORE_API_URL}/projects/{self.settings.FIREBASE_PROJECT_ID}/databases/(default)/documents"

    async def _get_headers(self) -> Dict[str, str]:
        token = await self.auth_service.get_valid_id_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        url: str,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        session = self._session or aiohttp.ClientSession()
        close_session = self._session is None
        try:
            headers = await self._get_headers()
            async with session.request(method, url, json=json_body, params=params, headers=headers) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise NetworkError(f"Firestore error {resp.status}: {text}")
                return await resp.json()
        finally:
            if close_session:
                await session.close()

    def _run_query_path(self, user_uid: str) -> str:
        return f"{self._base_url}/users/{user_uid}:runQuery"

    def _device_doc_path(self, user_uid: str, device_id: str) -> str:
        return f"{self._base_url}/users/{user_uid}/devices/{device_id}"

    def _sync_state_doc_path(self, user_uid: str, device_id: str) -> str:
        return f"{self._base_url}/users/{user_uid}/syncState/{device_id}"

    async def create_event(
        self,
        user_uid: str,
        device_id: str,
        event_id: str,
        event_type: str,
        entity_id: str,
        payload: Dict[str, Any],
    ) -> str:
        """Crea un evento de sincronización en Firestore y retorna su ID."""
        now_iso = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        doc_name = (
            f"projects/{self.settings.FIREBASE_PROJECT_ID}/databases/(default)/documents/"
            f"users/{user_uid}/events/{event_id}"
        )

        body = {
            "writes": [
                {
                    "update": {
                        "name": doc_name,
                        "fields": {
                            "type": {"stringValue": event_type},
                            "entityId": {"stringValue": entity_id},
                            "originDeviceId": {"stringValue": device_id},
                            "schemaVersion": {"integerValue": 1},
                            "payload": self._to_firestore_value(payload),
                            "createdAt": {"timestampValue": now_iso},
                        },
                    },
                    "currentDocument": {"exists": False},
                },
            ]
        }

        url = (
            f"{self.settings.FIRESTORE_API_URL}/projects/{self.settings.FIREBASE_PROJECT_ID}"
            "/databases/(default)/documents:commit"
        )
        await self._request("POST", url, json_body=body)
        return event_id

    async def fetch_events_since(
        self,
        user_uid: str,
        since_timestamp: Optional[str] = None,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Obtiene eventos desde un timestamp (orden ascendente)."""
        query: Dict[str, Any] = {
            "structuredQuery": {
                "from": [{"collectionId": "events"}],
                "orderBy": [
                    {"field": {"fieldPath": "createdAt"}, "direction": "ASCENDING"},
                    {"field": {"fieldPath": "__name__"}, "direction": "ASCENDING"},
                ],
                "limit": page_size,
            }
        }

        if since_timestamp:
            query["structuredQuery"]["where"] = {
                "fieldFilter": {
                    "field": {"fieldPath": "createdAt"},
                    "op": "GREATER_THAN_OR_EQUAL",
                    "value": {"timestampValue": since_timestamp},
                }
            }

        url = self._run_query_path(user_uid)
        resp = await self._request("POST", url, json_body=query)

        events: List[Dict[str, Any]] = []
        for row in resp:
            doc = row.get("document")
            if not doc:
                continue
            event = self._from_firestore_document(doc)
            events.append(event)
        return events, None

    async def update_device_state(
        self,
        user_uid: str,
        device_id: str,
        last_event_id: Optional[str],
        last_sync_timestamp: Optional[str],
    ) -> None:
        """Actualiza el estado de sincronización del dispositivo."""
        fields: Dict[str, Any] = {
            "deviceId": {"stringValue": device_id},
            "updatedAt": {"timestampValue": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')},
        }
        if last_event_id:
            fields["lastAppliedEventId"] = {"stringValue": last_event_id}
        if last_sync_timestamp:
            fields["lastAppliedEventAt"] = {"timestampValue": last_sync_timestamp}

        body = {"fields": fields}
        url = self._device_doc_path(user_uid, device_id)
        await self._request("PATCH", url, json_body=body)

        sync_fields: Dict[str, Any] = {
            "updatedAt": {"timestampValue": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')},
        }
        if last_event_id:
            sync_fields["lastAppliedEventId"] = {"stringValue": last_event_id}
        if last_sync_timestamp:
            sync_fields["lastAppliedEventAt"] = {"timestampValue": last_sync_timestamp}

        sync_body = {"fields": sync_fields}
        sync_url = self._sync_state_doc_path(user_uid, device_id)
        await self._request("PATCH", sync_url, json_body=sync_body)

    def _from_firestore_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        fields = doc.get("fields", {})
        result = {"id": doc.get("name", "").split("/")[-1]}
        for key, value in fields.items():
            result[key] = self._from_firestore_value(value)
        return result

    def _from_firestore_value(self, value: Dict[str, Any]) -> Any:
        if "stringValue" in value:
            return value["stringValue"]
        if "integerValue" in value:
            return int(value["integerValue"])
        if "doubleValue" in value:
            return float(value["doubleValue"])
        if "booleanValue" in value:
            return bool(value["booleanValue"])
        if "timestampValue" in value:
            return value["timestampValue"]
        if "mapValue" in value:
            fields = value.get("mapValue", {}).get("fields", {})
            return {k: self._from_firestore_value(v) for k, v in fields.items()}
        if "arrayValue" in value:
            values = value.get("arrayValue", {}).get("values", [])
            return [self._from_firestore_value(v) for v in values]
        return None

    def _to_firestore_value(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {"nullValue": None}
        if isinstance(value, bool):
            return {"booleanValue": value}
        if isinstance(value, int):
            return {"integerValue": value}
        if isinstance(value, float):
            return {"doubleValue": value}
        if isinstance(value, str):
            # Check if string is ISO 8601 timestamp format (ends with 'Z' or has timezone)
            if self._is_iso_timestamp(value):
                return {"timestampValue": value}
            return {"stringValue": value}
        if isinstance(value, dict):
            return {
                "mapValue": {
                    "fields": {k: self._to_firestore_value(v) for k, v in value.items()}
                }
            }
        if isinstance(value, list):
            return {"arrayValue": {"values": [self._to_firestore_value(v) for v in value]}}
        return {"stringValue": str(value)}

    def _is_iso_timestamp(self, value: str) -> bool:
        """Check if string is ISO 8601 timestamp (e.g., 2026-02-06T15:30:45.123456Z)"""
        if not isinstance(value, str):
            return False
        # Must end with 'Z' or have timezone offset (+00:00, -05:00, etc.)
        if value.endswith('Z'):
            return True
        # Check for timezone offset pattern
        if len(value) >= 19:  # Minimum YYYY-MM-DDTHH:MM:SS
            if value[-6] in ('+', '-') and value[-3] == ':':
                return True
        return False
    # ==================== INITIAL SYNC (Full snapshot) ====================

    async def get_all_accounts(self, user_uid: str) -> List[Dict[str, Any]]:
        """Obtiene todas las cuentas del usuario para sincronización inicial."""
        query_body = {
            "structuredQuery": {
                "from": [{"collectionId": "accounts"}],
                "where": None,
            }
        }
        try:
            result = await self._request(
                "POST",
                self._run_query_path(user_uid),
                json_body=query_body,
            )
            accounts = []
            if isinstance(result, list):
                for row in result:
                    doc = row.get("document")
                    if doc:
                        accounts.append(self._extract_doc_fields(doc))
            return accounts
        except Exception as e:
            raise NetworkError(f"Error fetching accounts: {str(e)}")

    async def get_all_categories(self, user_uid: str) -> List[Dict[str, Any]]:
        """Obtiene todas las categorías del usuario."""
        query_body = {
            "structuredQuery": {
                "from": [{"collectionId": "categories"}],
                "where": None,
            }
        }
        try:
            result = await self._request(
                "POST",
                self._run_query_path(user_uid),
                json_body=query_body,
            )
            categories = []
            if isinstance(result, list):
                for row in result:
                    doc = row.get("document")
                    if doc:
                        categories.append(self._extract_doc_fields(doc))
            return categories
        except Exception as e:
            raise NetworkError(f"Error fetching categories: {str(e)}")

    async def get_all_budgets(self, user_uid: str) -> List[Dict[str, Any]]:
        """Obtiene todos los presupuestos del usuario."""
        query_body = {
            "structuredQuery": {
                "from": [{"collectionId": "budgets"}],
                "where": None,
            }
        }
        try:
            result = await self._request(
                "POST",
                self._run_query_path(user_uid),
                json_body=query_body,
            )
            budgets = []
            if isinstance(result, list):
                for row in result:
                    doc = row.get("document")
                    if doc:
                        budgets.append(self._extract_doc_fields(doc))
            return budgets
        except Exception as e:
            raise NetworkError(f"Error fetching budgets: {str(e)}")

    async def get_all_transactions(self, user_uid: str) -> List[Dict[str, Any]]:
        """Obtiene todas las transacciones del usuario."""
        query_body = {
            "structuredQuery": {
                "from": [{"collectionId": "transactions"}],
                "where": None,
                "limit": 1000,  # Límite para no descargar demasiado de una vez
            }
        }
        try:
            result = await self._request(
                "POST",
                self._run_query_path(user_uid),
                json_body=query_body,
            )
            transactions = []
            if isinstance(result, list):
                for row in result:
                    doc = row.get("document")
                    if doc:
                        transactions.append(self._extract_doc_fields(doc))
            return transactions
        except Exception as e:
            raise NetworkError(f"Error fetching transactions: {str(e)}")

    def _extract_doc_fields(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae campos de un documento de Firestore."""
        fields = doc.get("fields", {})
        result = {"id": doc.get("name", "").split("/")[-1]}  # Últimos segmento del path es el ID
        for key, value in fields.items():
            result[key] = self._from_firestore_value(value)
        return result