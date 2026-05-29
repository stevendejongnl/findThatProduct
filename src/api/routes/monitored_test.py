import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from src.api.main import create_app


@pytest.fixture
def app_with_monitoring():
    with patch.dict("os.environ", {"CHANGEWATCH_URL": "http://cw.test", "CHANGEWATCH_NOTIFY_CHANNELS": "telegram"}):
        return create_app()


@pytest.fixture
def app_no_monitoring():
    with patch.dict("os.environ", {}, clear=False):
        import os
        os.environ.pop("CHANGEWATCH_URL", None)
        return create_app()


async def test_config_monitoring_enabled(app_with_monitoring):
    async with AsyncClient(transport=ASGITransport(app=app_with_monitoring), base_url="http://test") as client:
        resp = await client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["monitoring_enabled"] is True


async def test_config_monitoring_disabled(app_no_monitoring):
    async with AsyncClient(transport=ASGITransport(app=app_no_monitoring), base_url="http://test") as client:
        resp = await client.get("/api/config")
    assert resp.status_code == 200
    assert resp.json()["monitoring_enabled"] is False


async def test_post_monitored_creates_and_triggers(app_with_monitoring):
    mock_client = AsyncMock()
    mock_client.enabled = True
    with patch("src.api.routes.monitored.get_changewatch_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app_with_monitoring), base_url="http://test") as client:
            resp = await client.post("/api/monitored", json={
                "name": "Sony WH-1000XM5",
                "ean": "4548736134034",
                "currency": "EUR",
                "schedule": "0 */6 * * *",
            })
    assert resp.status_code == 201
    mock_client.save_monitor.assert_called_once()
    mock_client.trigger_run.assert_called_once()


async def test_post_monitored_returns_503_when_disabled(app_no_monitoring):
    async with AsyncClient(transport=ASGITransport(app=app_no_monitoring), base_url="http://test") as client:
        resp = await client.post("/api/monitored", json={
            "name": "Sony WH-1000XM5",
            "ean": "4548736134034",
            "currency": "EUR",
            "schedule": "0 */6 * * *",
        })
    assert resp.status_code == 503


async def test_get_monitored_returns_list(app_with_monitoring):
    mock_client = AsyncMock()
    mock_client.enabled = True
    mock_client.list_monitors.return_value = [
        {"monitor_name": "ftp_4548736134034", "last_value": "€329,00", "ran_at": "2026-05-28 12:00:00", "status": "ok"},
        {"monitor_name": "tp-link_deco_x50", "last_value": "€219,00", "ran_at": "2026-05-28 10:00:00", "status": "ok"},
    ]
    def get_source_side_effect(name):
        if name == "ftp_4548736134034":
            return '_PRODUCT_NAME = "Sony WH-1000XM5"\n_EAN = "4548736134034"\n_CURRENCY = "EUR"\n_QUERY = "4548736134034"\n_URL = ""\n'
        return '_PRODUCT_NAME = "TP-Link Deco X50 (1-pack)"\nmonitor = Monitor(\n    name="tp-link_deco_x50",\n    url="https://tweakers.net/pricewatch/123/tp-link.html",\n)\n'
    mock_client.get_source = AsyncMock(side_effect=get_source_side_effect)
    mock_client.get_runs.return_value = [
        {"last_value": "€329,00", "ran_at": "2026-05-28 12:00:00"},
        {"last_value": "€335,00", "ran_at": "2026-05-28 06:00:00"},
    ]
    mock_client.get_metrics.return_value = [{"v": 335.0}, {"v": 329.0}]
    with patch("src.api.routes.monitored.get_changewatch_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app_with_monitoring), base_url="http://test") as client:
            resp = await client.get("/api/monitored")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    ftp = next(d for d in data if d["id"] == "ftp_4548736134034")
    assert ftp["name"] == "Sony WH-1000XM5"
    assert ftp["current_price"] == 329.0
    assert ftp["trend"] == "down"
    assert ftp["history"] == [335.0, 329.0]
    tplink = next(d for d in data if d["id"] == "tp-link_deco_x50")
    assert tplink["name"] == "TP-Link Deco X50 (1-pack)"
    assert tplink["url"] == "https://tweakers.net/pricewatch/123/tp-link.html"


async def test_get_monitored_returns_503_when_disabled(app_no_monitoring):
    async with AsyncClient(transport=ASGITransport(app=app_no_monitoring), base_url="http://test") as client:
        resp = await client.get("/api/monitored")
    assert resp.status_code == 503


async def test_delete_monitored_calls_client(app_with_monitoring):
    mock_client = AsyncMock()
    mock_client.enabled = True
    with patch("src.api.routes.monitored.get_changewatch_client", return_value=mock_client):
        async with AsyncClient(transport=ASGITransport(app=app_with_monitoring), base_url="http://test") as client:
            resp = await client.delete("/api/monitored/ftp_4548736134034")
    assert resp.status_code == 204
    mock_client.delete_monitor.assert_called_once_with("ftp_4548736134034")
