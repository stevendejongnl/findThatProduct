import asyncio
import os
import re
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.application.monitor_template import make_monitor_name, render_monitor
from src.infrastructure.changewatch_client import ChangeWatchClient

router = APIRouter()

_METADATA_PATTERNS = {
    "product_name": re.compile(r'_PRODUCT_NAME\s*=\s*["\']([^"\']*)["\']'),
    "ean":          re.compile(r'_EAN\s*=\s*["\']([^"\']*)["\']'),
    "currency":     re.compile(r'_CURRENCY\s*=\s*["\']([^"\']*)["\']'),
}


def get_changewatch_client() -> ChangeWatchClient:
    return ChangeWatchClient.from_env()


def _parse_metadata(source: str) -> dict:
    return {k: (m.group(1) if (m := p.search(source)) else None) for k, p in _METADATA_PATTERNS.items()}


def _trend(runs: list[dict]) -> str:
    values = []
    for r in runs:
        try:
            values.append(float(r["last_value"]))
        except (TypeError, ValueError):
            pass
    if len(values) < 2:
        return "flat"
    if values[0] < values[1]:
        return "down"
    if values[0] > values[1]:
        return "up"
    return "flat"


async def _enrich_monitor(monitor: dict, client: ChangeWatchClient) -> dict | None:
    name = monitor["monitor_name"]
    try:
        source, runs, metrics = await asyncio.gather(
            client.get_source(name),
            client.get_runs(name, limit=2),
            client.get_metrics(name, hours=720),
        )
    except Exception:
        return None

    meta = _parse_metadata(source)
    history = [p["_value"] for p in metrics if "_value" in p]

    try:
        current_price = float(monitor["last_value"]) if monitor.get("last_value") else None
    except (TypeError, ValueError):
        current_price = None

    return {
        "id": name,
        "name": meta["product_name"] or name,
        "ean": meta["ean"] or None,
        "currency": meta["currency"] or "EUR",
        "current_price": current_price,
        "last_checked": monitor.get("ran_at"),
        "status": monitor.get("status"),
        "trend": _trend(runs),
        "history": history,
    }


class MonitorRequest(BaseModel):
    name: str
    ean: str | None = None
    currency: str = "EUR"
    schedule: str = "0 */6 * * *"


@router.get("/config")
async def get_config(request: Request) -> dict:
    return {"monitoring_enabled": bool(getattr(request.app.state, "monitoring_enabled", False))}


@router.post("/monitored", status_code=201)
async def create_monitored(body: MonitorRequest) -> dict:
    client = get_changewatch_client()
    if not client.enabled:
        raise HTTPException(status_code=503, detail="Monitoring not configured")

    notify_channels = [c.strip() for c in os.getenv("CHANGEWATCH_NOTIFY_CHANNELS", "").split(",") if c.strip()]
    monitor_name = make_monitor_name(ean=body.ean, title=body.name)
    source = render_monitor(
        name=monitor_name,
        product_name=body.name,
        ean=body.ean,
        currency=body.currency,
        schedule=body.schedule,
        notify_channels=notify_channels,
    )
    await client.save_monitor(monitor_name, source)
    await client.trigger_run(monitor_name)
    return {"id": monitor_name}


@router.get("/monitored")
async def list_monitored() -> list[dict]:
    client = get_changewatch_client()
    if not client.enabled:
        raise HTTPException(status_code=503, detail="Monitoring not configured")

    all_monitors = await client.list_monitors()
    ftp_monitors = [m for m in all_monitors if m["monitor_name"].startswith("ftp_")]
    results = await asyncio.gather(*[_enrich_monitor(m, client) for m in ftp_monitors])
    return [r for r in results if r is not None]


@router.delete("/monitored/{name}", status_code=204)
async def delete_monitored(name: str) -> None:
    client = get_changewatch_client()
    if not client.enabled:
        raise HTTPException(status_code=503, detail="Monitoring not configured")
    await client.delete_monitor(name)
