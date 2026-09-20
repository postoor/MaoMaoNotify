# MaoMaoNotify Server

Async FastAPI backend (Python 3.13+), uv-managed. Multi-user from day one.

## Dev

```bash
uv sync
uv run uvicorn app.main:app --reload   # http://localhost:8000
uv run pytest                          # tests (Phase 1+)
uv run ruff check .                    # lint
uv run alembic upgrade head            # migrations (once models exist)
```

## app/ packages

Each package's responsibility is documented in its `__init__.py`. Core pipeline
(§3): **Presence → Routing → Policy → Presentation**, with the invariant
**User Policy > Device Policy > Agent Request**.

Skeleton only: `app.main` currently exposes just `GET /health`.
