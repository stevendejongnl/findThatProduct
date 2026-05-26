# ── Python app ─────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY src/ ./src/

ENV PORT=8000
ENV LOG_LEVEL=info
ENV ALLOWED_ORIGINS=*

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
