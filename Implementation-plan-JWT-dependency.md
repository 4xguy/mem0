• # Auth0‑Bound Identity Plan (Mem0 + mem0ctl)

  ## Objective

  Bind every memory operation to the authenticated Auth0 user. Make the “effective user” the JWT subject (sub) by default, enforce ownership on writes, and keep a simple, predictable UX
  across CLI and agents (Codex, Claude, Gemini).

  ## Scope

  - mem0 (FastAPI server at https://mem0.icvida.com)
  - memory‑cli (mem0ctl)
  - Optional future: gateway for web tools (ChatGPT Actions / MCP) — out of critical path

  ## Assumptions

  - Auth0 tenant exists; Device Code (CLI) + M2M (service) apps configured.
  - mem0 already live (Postgres+pgvector, LLM key). JSON error envelope is stable.
  - Existing memories may use ad‑hoc user IDs (e.g., “keith”).

  ———

  ## Design Overview

  - Identity: JWT “subject” (sub) is the canonical user identifier.
  - Server (mem0):
      - Require valid Auth0 JWT on all routes except /health.
      - Default user_id = sub if omitted.
      - Enforce ownership on add/search/update/delete/reset; allow cross‑user only with admin scope.
  - CLI (mem0ctl):
      - After login, default --user to JWT sub (omit --user in requests).
      - Allow --user override only for admin tokens; otherwise reject.

  ———

  ## Server Changes (mem0)

  ### 1) JWT verification

  - Env:
      - AUTH0_DOMAIN, AUTH0_AUDIENCE
  - Dependency/utility:
      - JWKS fetch + cache (RS256 only), verify_jwt(token) → claims with issuer/audience checks.
  - FastAPI integration:
      - get_identity dependency extracts Authorization: Bearer …, verifies, and returns Identity(sub, scopes, jwks_cache_hit?).
      - Apply to all routes except /health.

  ### 2) Ownership & access rules

  - Read/search:
      - If no identifier: default user_id = sub.
      - If identifier present and not equal to sub → 403 unless mem0:admin.
  - Write/update/delete/reset:
      - For update/delete: fetch record, ensure payload.user_id == sub → else 403 (unless admin).
      - For add: force user_id = sub if omitted; if provided and ≠ sub → 403 (unless admin).
  - Errors:
      - Continue using { "error": { "code", "message", "details?" } } envelope.

  ### 3) Scopes

  - mem0:read, mem0:write, optional mem0:admin.
  - Enforce read/write by scope; admin can access other users.

  ### 4) Documentation

  - deploy/README.md: Auth0 env, curl examples (401→200), ownership rules, scope mapping.

  Acceptance

  - 401 on missing/invalid token.
  - Default to sub when user_id omitted.
  - 403 on cross‑user ops without admin.
  - Existing JSON error shape preserved.

  ———

  ## CLI Changes (memory‑cli)

  ### 1) Default identity

  - After login, whoami caches claims.sub.
  - Effective default user = sub. Do not send user_id unless explicitly set.
  - config show displays default_user=<sub>.

  ### 2) Admin override

  - --user <id> allowed only if token has mem0:admin; otherwise error with an explanation.
  - Docs: “Override only for admin and special cases.”

  ### 3) Requests & output

  - All commands (search, add, update, delete, reset) omit user_id by default → server binds to sub.
  - Preserve retry/backoff and single‑line error summarization.

  ### 4) Documentation & tests

  - README/CLI_CHEATSHEET: “Default user is your Auth0 subject. Use --user only with admin.”
  - Tests: default flow uses sub; cross‑user attempts return 403 w/ summarized error.

  Acceptance

  - mem0ctl add/search (no --user) binds to the logged‑in user.
  - mem0ctl update/delete/reset enforce ownership.
  - mem0ctl --user other fails without admin scope.

  ———

  ## Migration (optional)

  Goal: move legacy “keith” records under your Auth0 sub.

  - Script:
      - search --user keith -> collect IDs.
      - For each ID: update payload.user_id → <sub>, reindex as needed.
      - Dry‑run and backup file of migrated IDs.
  - Verify: search as <sub> returns expected records; keith no longer used.

  Acceptance

  - Queries tied to Auth0 sub yield the directive and durable facts.
  - No functional changes needed in CLI after migration.

  ———

  ## Optional: Gateway (later)

  - Front a tiny FastAPI gateway to:
      - Verify JWT and forward to mem0.
      - Offer compact tool responses for web UIs (/search with summary=true).
  - Not required for CLI; defer until needed.

  ———

  ## Security Model

  - Token source: Auth0 (Device Code for CLI, Client Credentials for services).
  - Authorization:
      - Read: mem0:read scoped to own sub by default.
      - Write: mem0:write scoped to own sub.
      - Admin: mem0:admin allows cross‑user access (with audit logging, optional).
  - Transport: HTTPS only; keep /health public; protect /docs if desired.

  ———

  ## Operator Notes

  - Dokploy:
      - Set AUTH0_DOMAIN, AUTH0_AUDIENCE, and existing envs.
      - Health: /health.
  - Observability:
      - Log 401/403 counts; sample user binding events (no token content).

  ———

  ## Testing Plan

  - Server unit/integration:
      - JWT valid/invalid cases (issuer, aud, signature, exp).
      - Default user_id = sub behavior.
      - Cross‑user 403 non‑admin vs. 200 admin.
      - Ownership checks on update/delete.
  - CLI tests:
      - Default sub binding; implicit user.
      - Admin override allowed; non‑admin denied (403 summarized).

  ———

  ## Rollout Plan

  1. Implement server auth dependency & route guards; deploy behind feature flag (optional).
  2. Update CLI default user behavior; release minor version.
  3. Migrate legacy records (optional).
  4. Flip enforcement on in production; monitor errors.
  5. (Optional) add gateway for web tools.

  ———

  ## Risks & Mitigations

  - Misconfigured Auth0 (aud/iss mismatch) → clear 401 with how‑to.
  - Cross‑user workflows break → use admin tokens or keep alias mapping temporarily.
  - Token refresh issues → retry login; CLI handles Device Code + refresh.

  ———

  ## Open Questions

  - Should service accounts be allowed to “act_as” a user via a custom claim? (Defer; start strict.)
  - Keep /docs open or Auth0‑gated? (Operator choice.)
  - Add audit logging for admin cross‑user writes? (Nice‑to‑have.)

  ———

  ## Appendix

  ### Server env

  AUTH0_DOMAIN=dev-<tenant>.us.auth0.com
  AUTH0_AUDIENCE=https://mem0.icvida.com/api
  OPENAI_API_KEY=...
  POSTGRES_HOST=...
  MEM0_RATE_LIMIT_PER_MINUTE=0

  ### CLI usage (post‑change)

  # defaults to your Auth0 subject (no --user needed)
  mem0ctl add --text "Prefers dark mode"
  mem0ctl search --query "preferences" -n 3 --summary
  mem0ctl update <id> --text "UPDATED: ..."
  mem0ctl delete <id>
  mem0ctl reset  # requires explicit --user only for admin override

  ### Error envelope (unchanged)

  {
    "error": {
      "code": "FORBIDDEN",
      "message": "Cross-user access requires mem0:admin",
      "details": {"user_id": "requested", "sub": "caller"}
    }
  }

  ———

  This plan keeps the implementation small: a JWT dependency + ownership checks on the server, a default‑to‑sub behavior in the CLI, and optional migration. Codex/Claude can break down
  each bullet into concrete TODOs (files to touch, tests to add, exact code blocks) during implementation.
