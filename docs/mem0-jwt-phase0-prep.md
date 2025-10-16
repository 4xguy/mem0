# Mem0 JWT Identity – Phase 0 Prep

## Auth0 Configuration Baseline
- Required variables: `AUTH0_DOMAIN` and `AUTH0_AUDIENCE` now live in `server/.env.example` and the Dokploy checklist; populate them per tenant (e.g., `dev-<tenant>.us.auth0.com`, `https://mem0.icvida.com/api`).
- Action: confirm both values with the Auth0 tenant owner and capture them alongside the existing secrets in Dokploy (`deploy/README.md`).
- Tracking: add the confirmed values to the internal deployment secrets inventory before Phase 1 starts; note who validated them and on which date.

## Route Exposure Audit (server/main.py)
| Path | Methods | Current Auth Behaviour | Target State |
| --- | --- | --- | --- |
| `/health` (`server/main.py:362`) | GET | No auth, readiness check | Remains public |
| `/` (`server/main.py:347`) | GET | Redirect to `/docs` | Gate behind JWT or leave open only for local dev |
| `/docs`, `/openapi.json`, `/redoc` | GET | FastAPI auto-generated, public | Decide whether to gate via dependency or rely on reverse-proxy rules |
| `/configure` (`server/main.py:206`) | POST | Open | Require Auth0 JWT (admin scope only) |
| `/memories` (`server/main.py:216`, `server/main.py:234`) | POST, GET | Open | Require JWT; default user → caller sub |
| `/memories/{memory_id}` (`server/main.py:253`, `server/main.py:291`) | GET, PUT | Open | Require JWT; ownership enforced |
| `/memories/{memory_id}/history` (`server/main.py:277`) | GET | Open | Require JWT; ownership enforced |
| `/search` (`server/main.py:239`) | POST | Open | Require JWT; default filters to caller sub |
| `/memories` (`server/main.py:311`) | DELETE | Open | Require JWT; admin or self |
| `/reset` (`server/main.py:327`) | POST | Open | Require JWT; admin or self |
| `/whoami` (`server/main.py:333`) | GET | Best-effort reflection, no auth today | Decide whether to keep public for debugging or protect with JWT |

Observations:
- Rate limit middleware (`server/main.py:135`) already whitelists `/health`, `/docs`, `/openapi.json`; align JWT exemption list with that.
- When gating auto docs, ensure local dev instructions mention how to obtain a token for `/docs` testing.

## Existing `user_id` Usage Inventory
- Server validation: endpoints require at least one identifier (`user_id`, `agent_id`, or `run_id`) but never default to the caller; see `add_memory` guard (`server/main.py:216-223`) and matching checks on retrieval/deletion routes.
- Backend API: `Memory` operations expect explicit identifiers; search paths pass through whatever the client supplied without mutation (`server/main.py:239-275`).
- Vector/graph stores index by `user_id` strings (e.g., `mem0/vector_stores/valkey.py:23`, `mem0/memory/kuzu_memory.py:153`), so legacy non-Auth0 identifiers will persist until rewritten.
- Client layer: higher-level helpers (e.g., `mem0/client/main.py:1201-1350`) accept `user_id` kwargs but provide no implicit default, mirroring the server contract.
- Implication: historical memories tagged with ad-hoc IDs (like "keith") will continue to resolve unless migrated; Phase 3 must enforce strict subject matching before insert/update/delete covers these.

## Pending Follow-ups
- Log the confirmed Auth0 values in your shared deployment tracker with owner + date.
- Decide on exposure policy for `/docs` and `/whoami` before Phase 1 to avoid surprises during dependency wiring.
- Draft migration stories for legacy identifiers once admin tooling is finalised.
