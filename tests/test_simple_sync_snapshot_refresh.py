import pytest

from gf_mobile.sync.simple_sync import SimpleSyncService


class _FakeSyncProtocol:
    def __init__(self):
        self.calls = []

    async def push_outbox(self, limit: int = 100):
        self.calls.append(("push", limit))
        return 2

    async def pull_and_apply(self, page_size: int = 50):
        self.calls.append(("pull", page_size))
        return 3

    async def refresh_base_snapshot(self):
        self.calls.append(("snapshot", None))
        return {"accounts": 1}

    def get_last_pull_timestamp(self):
        return None


@pytest.mark.asyncio
async def test_sync_now_refreshes_base_snapshot_after_pull() -> None:
    protocol = _FakeSyncProtocol()
    service = SimpleSyncService(protocol)

    result = await service.sync_now(push_limit=7, pull_limit=9)

    assert result.success is True
    assert result.pushed == 2
    assert result.pulled == 3
    assert protocol.calls == [
        ("push", 7),
        ("pull", 9),
        ("snapshot", None),
    ]
