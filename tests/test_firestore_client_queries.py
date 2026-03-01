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
