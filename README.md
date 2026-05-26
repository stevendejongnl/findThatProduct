# findThatProduct

Personal price comparison tool. Enter an EAN barcode or product name, get results from multiple sources ranked by price.

## Dev setup

```bash
uv sync
uv run pytest
uv run uvicorn src.api.main:app --reload
```

## API

`POST /api/search` — `{"query": "8710447308431"}` or `{"query": "peanut butter"}`

`GET /healthz` — health check

## Docker

```bash
docker-compose up
```

## Deploy

See `k8s/example/` for Kubernetes manifests. Copy to `k8s/` and fill in your values. Deploy via Keel (auto-updates on new image push).
