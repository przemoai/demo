# syntax=docker/dockerfile:1

# ---- builder: resolve and install dependencies with uv ----
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Dependencies only depend on pyproject.toml, so install them before the
# application source is copied in. Source-only changes below will not
# invalidate this layer.
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Now install the application itself (fast: dependencies are cached).
COPY app ./app
RUN uv sync --no-dev

# ---- runtime: minimal image, no build tooling ----
FROM python:3.14-slim-bookworm AS runtime
WORKDIR /app

RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

ENV PATH="/app/.venv/bin:${PATH}"

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
