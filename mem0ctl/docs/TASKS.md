## Implementation Tasks — mem0ctl

### Phase 1 — Repo bootstrap
- Init repo (MIT/Apache 2.0), set `mem0ctl/` package layout.
- Scaffolding: CLI entry, config loader, HTTP client, serializers.
- Add `.editorconfig`, CI lint/test, basic README.

### Phase 2 — Auth foundations
- Add OIDC Device Code flow for CLI (`login`, `logout`, `whoami`).
- Add service‑account Client Credentials support.
- Add API key/HMAC fallback path (env and config support).

### Phase 3 — Core commands
- `search`: query by `user_id|agent_id|run_id`, `limit`, `--summary`.
- `add`: accept `--role` and `--text` (or read from stdin); optional metadata.
- `update`, `delete`, `reset`: admin guarded.
- Output modes: JSON (default) and `--pretty`.

### Phase 4 — Optional local shim
- `serve`: start a local HTTP endpoint (127.0.0.1) for tools that only speak HTTP.
- Expose `/search` and `/add` locally; forward upstream with auth headers injected.

### Phase 5 — Integrations
- ChatGPT Actions: generate OpenAPI spec + OAuth config.
- Claude MCP: ultra‑minimal tool schema (search/add), small response payload.
- Codex/Claude Code/Warp/gemini-cli snippets.

### Phase 6 — Packaging & release
- Build single binaries per OS (PyInstaller or Node pkg).
- Add Homebrew/pipx install recipes.
- Versioning + changelog.

### Phase 7 — Hardening & Ops
- Retries/backoff, error messages, timeouts.
- Rate limit + optional `mem0-gateway` with JWT verification and HMAC.
- Basic telemetry flags.

Notes: final sub‑steps (e.g., exact flag names, test cases per edge condition) are left for Codex/Claude Code to generate via their own TODO lists during implementation.

