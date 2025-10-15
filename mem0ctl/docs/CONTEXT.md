## Context & Assumptions — mem0ctl

### Current Environment
- Mem0 REST: `https://mem0.icvida.com` (health = ok)
- Backing stores: Postgres (pgvector), Neo4j (external Bolt), LLM key present.
- Goal: Secure, token‑efficient memory access shared by many agents.

### Constraints
- Some agents can run local commands (Codex CLI, Claude Code, Warp, gemini-cli). Others (ChatGPT/Claude web) need HTTP tooling (Actions/MCP).
- MCP tool output counts toward context; we’ll keep schemas and responses minimal.

### Security Requirements
- Do not expose unauthenticated memory endpoints on the public internet.
- Support human login (CLI) and headless service accounts.
- Prefer OIDC; provide API key/HMAC fallback where OAuth is unavailable.

### Items To Research/Decide (before implementation)
1) OIDC Provider: Auth0 vs Cloudflare Access vs AWS Cognito (billing, issuer URL, device code support, JWKS cache TTLs).
2) ChatGPT Actions: confirm OAuth client registration and required scopes, finalize OpenAPI action spec.
3) Claude MCP: confirm current manifest format, size limits, and best practices for compact return payloads.
4) Packaging: Python (pipx + PyInstaller) vs Node (pkg/esbuild) distribution tradeoffs across macOS/Windows/Linux.
5) Logging/Telemetry: where to ship CLI/gateway logs (stdout only vs optional OTLP).

### API Contract Snapshot (Mem0 REST)
- POST `/memories`: body `{ messages: [{role, content}], user_id|agent_id|run_id }`
- POST `/search`: body `{ query, user_id|agent_id|run_id, limit? }` → `{ results: [...] }`
- GET `/memories?user_id=...` → list
- PUT `/memories/{id}` / DELETE `/memories/{id}`

### Naming & Identity
- Use `user_id` to tie a person across agents. Optional `agent_id` for persona‑specific memories.
- CLI config path: `~/.config/mem0/config.toml` and `~/.config/mem0/credentials.json`.

