import pytest
from aioresponses import aioresponses
from src.infrastructure.changewatch_client import ChangeWatchClient


@pytest.fixture
def client():
    return ChangeWatchClient(base_url="http://changewatch.test")


async def test_save_monitor_posts_source(client):
    with aioresponses() as m:
        m.post("http://changewatch.test/api/monitors/ftp_123/save", payload={"status": "ok"})
        await client.save_monitor("ftp_123", "# source code")


async def test_trigger_run_posts(client):
    with aioresponses() as m:
        m.post("http://changewatch.test/monitors/ftp_123/run", payload={"queued": "ftp_123"}, status=202)
        await client.trigger_run("ftp_123")


async def test_list_monitors_returns_list(client):
    with aioresponses() as m:
        m.get(
            "http://changewatch.test/api/monitors",
            payload=[{"monitor_name": "ftp_123", "last_value": "329.0", "ran_at": "2026-05-28 12:00:00", "status": "ok"}],
        )
        result = await client.list_monitors()
    assert result[0]["monitor_name"] == "ftp_123"


async def test_get_source_returns_source_string(client):
    with aioresponses() as m:
        m.get("http://changewatch.test/api/monitors/ftp_123/source", payload={"source": "# code"})
        result = await client.get_source("ftp_123")
    assert result == "# code"


async def test_get_runs_returns_list(client):
    with aioresponses() as m:
        m.get(
            "http://changewatch.test/api/monitors/ftp_123/runs?limit=2",
            payload=[{"last_value": "329.0", "ran_at": "2026-05-28 12:00:00"}],
        )
        result = await client.get_runs("ftp_123", limit=2)
    assert result[0]["last_value"] == "329.0"


async def test_get_metrics_returns_list(client):
    with aioresponses() as m:
        m.get(
            "http://changewatch.test/api/monitors/ftp_123/metrics?hours=720",
            payload=[{"_value": 329.0}, {"_value": 335.0}],
        )
        result = await client.get_metrics("ftp_123", hours=720)
    assert len(result) == 2


async def test_delete_monitor_sends_delete(client):
    with aioresponses() as m:
        m.delete("http://changewatch.test/api/monitors/ftp_123", payload={"status": "ok"})
        await client.delete_monitor("ftp_123")


async def test_disabled_client_list_returns_empty():
    client = ChangeWatchClient(base_url=None)
    result = await client.list_monitors()
    assert result == []


async def test_disabled_client_save_does_nothing():
    client = ChangeWatchClient(base_url=None)
    await client.save_monitor("ftp_123", "# source")


async def test_list_monitors_with_tag_passes_query_param(client):
    with aioresponses() as m:
        m.get(
            "http://changewatch.test/api/monitors?tag=findthatproduct",
            payload=[{"monitor_name": "ftp_123", "last_value": "329.0", "ran_at": "2026-05-28 12:00:00", "status": "ok"}],
        )
        result = await client.list_monitors(tag="findthatproduct")
    assert result[0]["monitor_name"] == "ftp_123"
