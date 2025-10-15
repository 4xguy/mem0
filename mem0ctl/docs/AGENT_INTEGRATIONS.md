## Agent Integrations — mem0ctl

### Codex CLI / Claude Code / Warp / gemini-cli
- Call the CLI directly:
  - `mem0ctl search --user <id> --query "..." --limit 3 --summary`
  - `mem0ctl add --user <id> --role user --text "..."`
- Prefer JSON output and include only the summary or top 1–2 items in prompts.

### Claude.ai (MCP)
- Provide a thin MCP server (future `mem0-mcp`) that forwards to Mem0 and returns compact payloads.
- Limit schema fields and response size; expose only `search` and `add`.

### ChatGPT (Actions)
- Host an OpenAPI spec with two paths: `/search` and `/memories`.
- Configure OAuth in the Action with your OIDC provider; scopes: `mem0:read`, `mem0:write`.
- Keep response schema minimal and paginate/limit aggressively.

### Server‑side agents (cron, pipelines)
- Use service account tokens (Client Credentials) and call Mem0 REST directly.

