# Dokploy Deployment Workflow

## Branch Layout
- `main`: Mirrors `upstream/main` (`https://github.com/mem0ai/mem0.git`). Never deploy from here; keep it clean for rebasing.
- `deploy/dokploy`: Long-lived branch that Dokploy watches. Holds MCP integration changes you want live on your server.
- `feat/<topic>`: Short-lived branches for development. Merge or rebase them into `deploy/dokploy` once tested.

## Daily Sync
```bash
# Refresh local main from upstream
git switch main
git fetch upstream
git rebase upstream/main

# Refresh deployment branch after syncing main
git switch deploy/dokploy
git rebase main
```

## Feature Workflow
```bash
git switch main
git switch -c feat/mcp-adapter
# ...implement changes...
git add <files>
git commit -m "feat: add MCP adapter"

git switch deploy/dokploy
git merge --no-ff feat/mcp-adapter
```
Use merge commits to preserve the feature history Dokploy deployed. After merging, delete the feature branch (`git branch -d feat/mcp-adapter`).

## Pre-Deploy Checklist
- `make lint` and `make test` (or targeted commands) pass.
- `pnpm test` inside `mem0-ts/` when TypeScript SDK changes exist.
- Update docs under `docs/` for new MCP endpoints or env variables.
- Review `deploy/dokploy` diff against `main` (`git diff main..deploy/dokploy`).

## Deploy
```bash
git push origin deploy/dokploy
```
Dokploy picks the latest commit and redeploys. Tag releases if desired (`git tag dokploy-YYYYMMDD && git push origin dokploy-YYYYMMDD`).

## Dokploy Configuration
- **Build:** set the Dokploy service to build from the repository root with the provided `Dockerfile`. Select branch `deploy/dokploy` and leave the build target default (`runtime`).
- **Environment variables:** map `AUTH0_DOMAIN`, `AUTH0_AUDIENCE`, and `OPENAI_API_KEY` (or other LLM credentials) along with any custom `POSTGRES_*`, `NEO4J_*`, `MEMGRAPH_*`, and `HISTORY_DB_PATH` values to point at your managed data stores. Set `MEM0_ALLOW_RUNTIME_CONFIG=1` only if you intend to enable the `/configure` endpoint; leave it unset/false in production. The defaults assume Postgres with pgvector, Neo4j, and a writable `/app/history/history.db`.
- **Ports:** expose port `8000` (the container listens on 0.0.0.0:8000). Configure Dokploy routing or load balancer rules accordingly.
- **Dependencies:** provision Postgres (with pgvector extension), Neo4j, and optional cache/vector stores as network-accessible services. Use Dokploy’s managed databases or external providers.
- **Health check:** hit `/docs` or `/memories` with a GET request after deploy to confirm the FastAPI app is serving traffic.

## Handling Hotfixes
```bash
git switch deploy/dokploy
git switch -c hotfix/<issue>
# ...apply fix...
git commit -am "fix: <summary>"
git switch deploy/dokploy
git merge --no-ff hotfix/<issue>
git push origin deploy/dokploy
git branch -d hotfix/<issue>
```
Backport the fix to `main` if it is not already there (`git switch main && git cherry-pick <commit>`).

## Environment & Secrets
- Store Dokploy manifests (e.g. `dokploy/app.yaml`) in this `deploy/` folder if they can be public. Otherwise maintain a `.env.example` with required variables.
- Confirm `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` with your Auth0 tenant owner before rollout and record them in Dokploy's secret inventory alongside other credentials.
- Never commit real secrets; Dokploy should inject them via its secret manager.

## Keeping Upstream Changes
- Periodically confirm `git status` on `main` is clean and `git status` on `deploy/dokploy` only shows expected differences.
- If a rebase introduces conflicts, resolve them on the feature branch before touching `deploy/dokploy`.


## Runtime Notes

### Auth scopes
- `mem0:read` for search/list/get/history operations; `mem0:write` for add/update/delete/reset; `mem0:admin` to act on other users or run destructive actions like `/reset` and `/configure`.
- Example 401 vs 403: `curl -H "Authorization: Bearer invalid" https://mem0.icvida.com/memories` → 401 `AUTH_HEADER_MISSING`; `curl -H "Authorization: Bearer $USER_TOKEN" -X DELETE https://mem0.icvida.com/memories/some-id` with a non-admin token → 403 `FORBIDDEN` detailing the missing scope.
- During rollout, verify Dokploy secrets inject the tenant-specific domain/audience and that service principals include the scopes above.

### Health check
- Configure Dokploy (or any load balancer) to poll `GET /health` every 10 seconds (timeout 5 seconds) so unhealthy pods are recycled automatically.
- The endpoint returns `{"status":"ok"}` when the Mem0 backend has initialised successfully.

### Error payload shape
All error responses share this envelope so clients can summarise failures easily:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests.",
    "details": {"limit": 60, "window": "1m"}
  }
}
```
Codes include `VALIDATION_ERROR`, `HTTP_ERROR`, `INTERNAL_ERROR`, and `RATE_LIMIT_EXCEEDED`.

### Rate limiting
- Optional env var: `MEM0_RATE_LIMIT_PER_MINUTE` (default `0`, disabled).
- When set > 0 the per-IP middleware returns 429 with the envelope above and a `Retry-After: 60` header.

### Identity probe
- `GET /whoami` returns `{ "status": "ok", "authorization": "Bearer …" }`, letting CLIs confirm which token (if any) was forwarded.
- `GET /health` remains the preferred readiness probe.

### Search summaries
- `POST /search` accepts `{ "summary": true, "max_summary_tokens": 150 }` to include a concise LLM-generated summary alongside results.
