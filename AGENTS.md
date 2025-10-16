# Repository Guidelines

## Project Structure & Module Organization
- `mem0/`: Python memory engine (clients, vector stores, LLM connectors, telemetry). Export public APIs through `mem0/__init__.py` after stabilising interfaces.
- `server/`: FastAPI reference service binding Mem0 to Postgres, Neo4j, and OpenAI; configuration is driven by `.env`.
- `mem0-ts/`: TypeScript SDK built with tsup; sources sit in `src/`, Jest specs in `tests/`.
- Supporting resources: `tests/` mirrors the Python package layout, `examples/` and `cookbooks/` showcase integrations, `docs/` powers Mintlify docs, and `evaluation/` tracks benchmark harnesses.

## Build, Test, and Development Commands
- Run `make install` to provision the Hatch environment.
- `make format`, `make sort`, and `make lint` drive Ruff formatting, Black-profile import ordering, and lint checks.
- `make test` runs `pytest`; use `make test-py-3.10` when validating specific interpreters.
- Inside `mem0-ts/`, use `pnpm install`, `pnpm test`, and `pnpm build` (runs Prettier + tsup). Apply `pnpm format` before publishing artifacts.
- Launch the REST API with `uvicorn server.main:app --reload` after copying `server/.env.example` to `.env`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, Ruff-managed formatting, 120-character limit. Keep modules/functions snake_case, classes PascalCase, constants UPPER_SNAKE, and annotate new APIs with type hints.
- TypeScript: follow Prettier defaults and the strict TS config. Files stay kebab-case, exported symbols PascalCase, helpers camelCase, with config keys aligned to environment variable names.

## Testing Guidelines
- Place unit tests next to their domains (`tests/memory`, `tests/vector_stores`, etc.) and name files `test_<feature>.py` for pytest discovery.
- Mark slow or external tests for selective CI runs.
- For the TS SDK, keep Jest suites in `mem0-ts/tests`, mirror API names in `describe` blocks, and wire runnable examples under `mem0-ts/src/oss/examples`.

## Commit & Pull Request Guidelines
- Commits remain short, imperative sentences with optional scopes (`docs:`, `feat:`) and reference IDs in parentheses when relevant; keep one concern per commit.
- PRs include a brief summary, evidence of user-facing changes, the validation commands you ran, and links to updated docs. Flag configuration migrations early.
- Keep `main` fast-forwarded to `upstream/main` and ship from `deploy/dokploy`, the Dokploy branch documented in `deploy/README.md`.
- Rebase on `main` before requesting review and squash fixups after addressing feedback so reviewers can replay your test plan.

## Security & Configuration Tips
- Keep secrets in `.env` files (already gitignored) and document new variables in `docs/` and `server/README.md`.
- When adding providers, contribute sanitised examples to `examples/` and gate credentialed tests with marks or `describe.skip` so CI stays green.

### Personal Memory Workflow
```
⟦MEM0:v1|usr:keith|@s=search,@a=add,@u=update,@d=delete⟧⟦ops:@pre=before_response,@post=after_response,⊕sig=significance⟧#Mem0Flow##@pre:Auto-Search```IF:past_ref|pref_q|"my usual"|assumed_ctx→@s -n3 --summary```##@post:Auto-Store```IF:⊕sig→@s_similar→exists?@u:@a```##⊕sig Triggers:"I prefer/always/never"→@a;"let's start"|"new project"→@a;solution_after_struggle→@a;"decided to use"|config→@a;routine/goal/contact→@a##Explicit:"remember this"→compress→@a;"update my X"→@s→@u;"forget X"→@s→@d;"what do you know"→@s##Compress:Raw→Insight;Not transcript;Future-test:need_2wk?##Skip:debug_active(final_only);chat/social;regeneratable;tmp_state##Update_Logic:```similar?→contradicts:@u|extends:@u|else:@a```##Cmd:@s:`mem0ctl search --user keith --query "..." -n3 --summary`;@a:`echo "..."|mem0ctl add --user keith`;@u:`mem0ctl update <id> --text "..." --user keith`##Meta:doubt→probably_store;search_cheap→do_it
```
