# syntax=docker/dockerfile:1.9

# Build React frontend
FROM node:20-alpine AS node-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
RUN npm run build

# Install Python deps with uv
FROM python:3.12-slim AS py-builder
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Install dependencies first
RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

# Copy application code and install the project
COPY pyproject.toml uv.lock README.md ./
COPY app/ ./app/
RUN --mount=type=cache,target=/root/.cache \
    uv sync --frozen --no-dev

# Lean runtime image
FROM python:3.12-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd -r app && useradd -r -g app -d /app app

COPY --from=py-builder --chown=app:app /app /app
COPY --from=node-builder --chown=app:app /frontend/dist /app/frontend/dist

USER app
WORKDIR /app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
