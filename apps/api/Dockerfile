FROM ghcr.io/astral-sh/uv:0.11.28-python3.12-trixie-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    PATH="/app/.venv/bin:$PATH"

RUN addgroup --system talentmatch && adduser --system --ingroup talentmatch talentmatch
WORKDIR /app
RUN mkdir -p /data && chown talentmatch:talentmatch /data

COPY apps/api/pyproject.toml ./pyproject.toml
COPY apps/api/uv.lock ./uv.lock
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

COPY apps/api/app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

USER talentmatch
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
