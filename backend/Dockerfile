# syntax=docker/dockerfile:1

# Dev: deps are synced at container start from the bind-mounted source (see docker-compose.yml),
# so edits on the host take effect without a rebuild.
FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS dev
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# Prod: a fixed, non-root runtime image with only the app + its locked (non-dev) deps.
FROM python:3.14-slim-trixie AS runtime
WORKDIR /app
RUN groupadd --system --gid 999 nonroot \
    && useradd --system --gid 999 --uid 999 --create-home nonroot
COPY --from=builder --chown=nonroot:nonroot /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER nonroot
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
