# Mem0 JWT Identity Rollout TODO

## Phase 0 – Alignment & Prep
- [x] Confirm Auth0 domain/audience values with ops and add them to deployment secrets inventory. Documented in `docs/mem0-jwt-phase0-prep.md` and surfaced in `server/.env.example`, `deploy/README.md`.
- [x] Audit FastAPI routers to list routes that must stay public (`/health`) versus those gated by JWT; see route table in `docs/mem0-jwt-phase0-prep.md`.
- [x] Inventory existing user_id usage patterns (including legacy IDs) to anticipate migration edge cases; findings captured in `docs/mem0-jwt-phase0-prep.md`.

## Phase 1 – JWT Verification Dependency
- [x] Select the JWKS client/caching approach and decide refresh / timeout policy. Implemented `JWKSCache` (600s TTL) in `server/auth.py`.
- [x] Implement a `verify_jwt` helper that enforces issuer, audience, expiration, and signature checks. Covered via `JWTVerifier.verify_token`.
- [x] Build a FastAPI security dependency (`require_identity`) that parses `Authorization` headers and returns identity details (sub, scopes, cache hit metadata).
- [x] Thread the dependency through all routers except `/health`, ensuring shared wiring for future endpoints (see `_identity` dependency usage in `server/main.py`).

## Phase 2 – Ownership & Access Enforcement
- [x] Default request context `user_id` to the caller's `sub` when omitted via `bind_user_to_identity`; applied to create/search/list/delete-all routes.
- [x] Add ownership validation to search/read paths; non-admin cross-user attempts now trigger `FORBIDDEN` with details through `bind_user_to_identity` and `ensure_memory_access`.
- [x] Enforce same-subject requirements on add/update/delete/reset flows, including payload mutation for add and admin-only reset.
- [x] Preserve the existing JSON error envelope for 401/403 responses using `json_error` across new authorization guards.

## Phase 3 – Scope Handling & Admin Overrides
- [x] Defined `mem0:read`, `mem0:write`, and `mem0:admin` helpers (`require_scope`, `require_scopes`) in `server/main.py` to guard each route.
- [x] Centralized admin overrides through `bind_user_to_identity` and `ensure_memory_access`, ensuring audit-friendly error details.
- [x] Reused the existing identity payload (`Identity.scopes`) so scope checks are available wherever dependencies run.

## Phase 4 – Documentation & Operator Enablement
- [x] Expanded `deploy/README.md` with scope mapping, 401/403 troubleshooting, and quick curl examples.
- [x] Added scope and troubleshooting sections (plus sample requests) to `docs/mem0-jwt-phase0-prep.md`.
- [x] Highlighted admin/default identity behavior so integrators plan for Auth0 subject binding.

## Phase 5 – Testing, Rollout, & Migration Support
- [x] Added FastAPI auth enforcement tests in `tests/server/test_auth.py` covering default-to-sub, scope failures, and admin overrides.
- [x] Documented rollout sequencing and 401/403 monitoring actions in `docs/mem0-jwt-phase0-prep.md`.
- [x] Captured legacy migration guidance (script reuse + tracking) so admins can rewrite historical `user_id` values post-rollout.
