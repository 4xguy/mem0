# Repository Guidelines

## Project Structure & Module Organization
- `mem0/`: core Python package (memory engine, vector stores, connectors). Public APIs surface via `mem0/__init__.py`.
- `server/`: FastAPI reference service binding Mem0 to Postgres, Neo4j, and OpenAI. Runtime config lives in `server/main.py`.
- `mem0-ts/`: TypeScript SDK (tsup build, Jest tests) under `src/` and `tests/`.
- `docs/`, `examples/`, `tests/`, and `deploy/` provide documentation, runnable samples, automated tests, and deployment manifests.

## Build, Test, and Development Commands
- `make install`: create the Hatch environment with all Python deps.
- `make format` / `make sort` / `make lint`: run Ruff formatting, import sorting, and lint checks.
- `make test`: execute the Python test suite via pytest.
- `pnpm install && pnpm test` in `mem0-ts/`: install Node deps and run SDK unit tests.
- Local API smoke test: `uvicorn server.main:app --reload` (requires `.env` per `server/.env.example`).

## Coding Style & Naming Conventions
- Python: 4-space indentation, Ruff-managed formatting, 120-char line soft limit. Modules/functions snake_case; classes PascalCase; constants UPPER_SNAKE.
- TypeScript: Prettier defaults, strict TS config. Files kebab-case, exported symbols PascalCase, helpers camelCase.
- Maintain shared formatting by running `make format` and `pnpm format` before commits.

## Testing Guidelines
- Python tests mirror the package under `tests/`; name files `test_<feature>.py`. Use pytest fixtures and mark slow/external tests.
- TypeScript tests live in `mem0-ts/tests` with Jest `describe` blocks matching API names.
- Auth hardening tests reside in `tests/server/test_auth.py`; run them before touching auth/identity flows: `python -m pytest tests/server/test_auth.py`.

## Commit & Pull Request Guidelines
- Commits follow short, imperative messages (`feat:`, `fix:`, `docs:`) with a single concern per commit.
- PRs should include a summary, validation commands (e.g., `make lint`, `python -m pytest tests/server/test_auth.py`), linked issues, and screenshots or logs when UI/API behavior changes.
- Rebase on `main` before requesting review and keep `deploy/dokploy` fast-forward to production.

## Security & Configuration Tips
- Secrets belong in `.env` files (ignored). Document new vars in `docs/` and `server/README.md`.
- Runtime reconfiguration is disabled unless `MEM0_ALLOW_RUNTIME_CONFIG=1`. Enable only in controlled environments.
- Auth0 tokens must carry `mem0:read`/`mem0:write`; assign `mem0:admin` sparingly and log cross-user operations.
