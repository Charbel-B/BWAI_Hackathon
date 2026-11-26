# API : Python 3.13, dépendances verrouillées par uv.lock, sans les outils de développement.
FROM python:3.13-slim AS api

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY backend/src ./src
RUN uv sync --locked --no-dev

# Les règles et les référentiels sont lus depuis la racine du dépôt (settings.REPO_ROOT).
COPY config /app/config
COPY data /app/data

ENV INVOICING_DATABASE_PATH=/app/var/invoicing.sqlite3
RUN useradd --create-home --uid 10001 app && mkdir -p /app/var && chown app /app/var
USER app

EXPOSE 8000
CMD [".venv/bin/uvicorn", "--factory", "invoicing.bootstrap:create_app", "--host", "0.0.0.0", "--port", "8000"]
