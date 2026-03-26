import pytest

from gf_mobile.sync.firestore_client import FirestoreClient


class _DummySettings:
    FIRESTORE_API_URL = "https://firestore.googleapis.com/v1"
    FIREBASE_PROJECT_ID = "project-test"


class _DummyAuthService:
    async def get_valid_id_token(self) -> str:
        return "token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "collection_name"),
    [
        ("get_all_accounts", "accounts"),
        ("get_all_categories", "categories"),
        ("get_all_budgets", "budgets"),
        ("get_all_transactions", "transactions"),
    ],
)
async def test_initial_snapshot_queries_do_not_send_null_where(method_name, collection_name):
    client = FirestoreClient(_DummySettings(), _DummyAuthService())
    captured = {}

    async def fake_request(method, url, json_body=None, params=None):
        captured["method"] = method
        captured["url"] = url
        captured["json_body"] = json_body
        return []

    client._request = fake_request  # type: ignore[method-assign]

    result = await getattr(client, method_name)("uid-1")

    assert result == []
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/users/uid-1:runQuery")
    structured_query = captured["json_body"]["structuredQuery"]
    assert structured_query["from"] == [{"collectionId": collection_name}]
    assert "where" not in structured_query


@pytest.mark.asyncio
async def test_get_all_transactions_paginates_until_last_page() -> None:
    client = FirestoreClient(_DummySettings(), _DummyAuthService())
    captured_offsets = []

    async def fake_request(method, url, json_body=None, params=None):
        structured = json_body["structuredQuery"]
        captured_offsets.append(structured.get("offset", 0))
        offset = structured.get("offset", 0)
        page_size = structured["limit"]
        if offset == 0:
            return [
                {
                    "document": {
                        "name": f"projects/x/documents/users/u/transactions/t{i}",
                        "fields": {},
                    }
                }
                for i in range(1, page_size + 1)
            ]
        if offset == page_size:
            return [{"document": {"name": "projects/x/documents/users/u/transactions/t1001", "fields": {}}}]
        return []

    client._request = fake_request  # type: ignore[method-assign]

    result = await client.get_all_transactions("uid-1")

    assert result[0]["id"] == "t1"
    assert result[-1]["id"] == "t1001"
    assert len(result) == 1001
    assert captured_offsets == [0, 1000]


@pytest.mark.asyncio
async def test_fetch_events_since_paginates_until_short_page() -> None:
    client = FirestoreClient(_DummySettings(), _DummyAuthService())
    captured_offsets = []

    async def fake_request(method, url, json_body=None, params=None):
        structured = json_body["structuredQuery"]
        captured_offsets.append(structured.get("offset", 0))
        offset = structured.get("offset", 0)
        if offset == 0:
            return [
                {
                    "document": {
                        "name": "projects/x/documents/users/u/events/e1",
                        "fields": {"createdAt": {"timestampValue": "2026-03-01T00:00:00Z"}},
                    }
                },
                {
                    "document": {
                        "name": "projects/x/documents/users/u/events/e2",
                        "fields": {"createdAt": {"timestampValue": "2026-03-01T00:01:00Z"}},
                    }
                },
            ]
        if offset == 2:
            return [
                {
                    "document": {
                        "name": "projects/x/documents/users/u/events/e3",
                        "fields": {"createdAt": {"timestampValue": "2026-03-01T00:02:00Z"}},
                    }
                }
            ]
        return []

    client._request = fake_request  # type: ignore[method-assign]

    events, cursor = await client.fetch_events_since(
        "uid-1",
        since_timestamp="2026-03-01T00:00:00Z",
        page_size=2,
    )

    assert cursor is None
    assert [event["id"] for event in events] == ["e1", "e2", "e3"]
    assert captured_offsets == [0, 2]
