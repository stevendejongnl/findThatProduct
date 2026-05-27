# ── Frontend build ──────────────────────────────────────────────────
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit
COPY frontend/ ./
RUN npm run build

# ── Python app ─────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

RUN uv run playwright install chromium --with-deps

COPY src/ ./src/
COPY --from=frontend /build/dist ./static/

ENV PORT=8000
ENV LOG_LEVEL=info
ENV ALLOWED_ORIGINS=*

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
