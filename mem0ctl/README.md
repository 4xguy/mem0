## mem0ctl — Unified Memory CLI for Agents

mem0ctl is a small, self‑contained CLI and optional gateway that connects many AI agents (Codex, Claude Code, ChatGPT Actions, Gemini, Warp, etc.) to your Mem0 server over a compact, token‑efficient workflow.

- Single source of truth: talks to your REST API at `https://mem0.icvida.com`.
- Token‑efficient: retrieves the top N memories and can return a short server‑side summary.
- Secure by default: OAuth 2.1/OIDC (Device Code for CLI), service accounts for servers, optional API‑key/HMAC fallback.

See docs:
- docs/TECHNICAL_PLAN.md — objectives, architecture, and decisions
- docs/CONTEXT.md — environment, assumptions, and research items
- docs/TASKS.md — granular implementation steps for Codex/Claude Code
- docs/SECURITY.md — auth design and hardening
- docs/AGENT_INTEGRATIONS.md — how to wire popular agents

## Quick idea of the UX
```bash
# search before answering
mem0ctl search --user customer-123 --query "delivery preferences" --limit 3 --summary

# add new facts after the turn
mem0ctl add --user customer-123 --role user --text "I prefer overnight shipping"
```

Configure with env vars or a config file:
- `MEM0_HOST=https://mem0.icvida.com`
- `MEM0_OIDC_ISSUER=...` `MEM0_OIDC_CLIENT_ID=...` (CLI performs OAuth Device Code)
- or `MEM0_API_KEY=...` (fallback)

The CLI is designed to be published as a standalone repo. This folder is a blueprint you can copy into a fresh repository.

