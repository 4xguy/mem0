# Technical Plan — mem0ctl

## Objectives
- Provide a token‑efficient, secure, and portable way for many agents to add/search memories against `https://mem0.icvida.com`.
- Be simple to deploy and use (one binary/CLI), while supporting robust auth for both humans (CLI) and services (agents, backends).

## Architecture (High Level)
- Component A: `mem0ctl` CLI
  - Subcommands: `search`, `add`, `update`, `delete`, `reset`, `login`, `whoami`, `serve` (optional local HTTP shim).
  - Output: compact JSON and an optional ~150‑token server‑side summary string.
  - Auth: OIDC Device Code flow (primary), API key/HMAC fallback. Caches tokens in `~/.config/mem0/credentials.json`.
- Component B (optional): `mem0-gateway` proxy
  - Enforces OAuth/JWT verification (and rate limits) in front of Mem0 REST.
  - Same endpoints as Mem0; forwards to `https://mem0.icvida.com`.
- Component C: minimal “integration packs”
  - ChatGPT Actions OpenAPI spec (OAuth).
  - Claude MCP tool (lean schema, short responses).
  - Agent-specific snippets (Codex CLI, Warp, gemini-cli).

## Authentication Strategy
1) OIDC (recommended):
   - Human users (CLI): OAuth Device Code 
   - Service accounts (backends): Client Credentials 
   - Providers: Auth0, Cloudflare Access, or Cognito (choose one; see CONTEXT.md).
   - Server verifies JWT via JWKS; tokens carry `sub`, `scope`, optional quotas.
2) API Key + HMAC (fallback):
   - Per‑user static key signs each request (`X-Mem0-Key`, `X-Mem0-Signature`, `X-Mem0-Timestamp`).
   - Gateway verifies signature and optional replay window.

## Token Efficiency
- Default `search` returns top 3–5 hits with `memory`, `score`, `created_at`.
- `--summary` flag asks server to compress results to ~150 tokens using your LLM key.
- Encourage agents to include only the summary or top 1–2 items in prompts.

## Deployment
- Publish `mem0ctl` as a standalone repo (Python or Node). CI builds a single binary per OS.
- Optionally deploy `mem0-gateway` (FastAPI) in front of Mem0 for centralized auth.

## Success Criteria
- Works with Codex CLI, Claude Code, Warp, gemini-cli out of the box.
- ChatGPT Actions + Claude MCP integrations available with minimal config.
- Round‑trip latencies < 300ms (excluding LLM summaries) and short responses by default.

## Open Decisions
- Pick the OIDC provider (Auth0 vs Cloudflare Access vs Cognito).
- Language for CLI (Python 3.12 vs Node 20). Default: Python for fastest POC.
- Whether to include the optional gateway now or later.

