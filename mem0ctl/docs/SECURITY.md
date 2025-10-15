## Security & Auth — mem0ctl

### Goals
- Authenticate humans (CLI) and services (agents/backends) with minimal friction.
- Keep public endpoints locked; prefer short‑lived tokens.

### Primary: OAuth 2.1 / OIDC
- CLI: Device Code flow → stores access/refresh tokens under `~/.config/mem0/credentials.json`.
- Services: Client Credentials flow with audience `mem0-api` and scopes: `mem0:read`, `mem0:write`.
- Server/gateway verifies JWT via JWKS; cache keys for 10–15 minutes.

### Fallback: API Key + HMAC
- Per user key `k`. Client signs `HMAC_SHA256(k, method|path|body|timestamp)`.
- Headers: `Authorization: ApiKey <id>`, `X-Mem0-Signature`, `X-Mem0-Timestamp`.
- Server enforces skew window (e.g., ±5 minutes) and nonce cache to prevent replay.

### Scopes & RBAC
- `mem0:read`, `mem0:write`, `mem0:admin`. Optional per‑user quotas.
- Service accounts restricted to specific `user_id` prefixes or tenants.

### Transport & Network
- HTTPS only. If Neo4j/Postgres are public, firewall to trusted sources.
- Optionally place `mem0-gateway` in front of Mem0 to centralize auth/rate limiting.

### Data Minimization
- Default search returns 3–5 results; enable `--summary` to compress before agents see content.
- Redaction hooks (optional) to strip PII.

