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
- Default request context `user_id` to the caller's `sub` when the payload omits the field.
- Add ownership validation to search/read paths; reject mismatched identifiers unless the caller has admin privileges.
- Enforce same-subject requirements on add/update/delete/reset flows, including payload mutation for add when user_id is omitted.
- Preserve the existing JSON error envelope when returning 401/403 responses and document new error codes/messages.

## Phase 3 – Scope Handling & Admin Overrides
- Define required scopes per operation (`mem0:read`, `mem0:write`, optional `mem0:admin`) and wire checks into the identity dependency.
- Ensure admin scope bypass paths are centralized and auditable; capture decision points for future logging.
- Update configuration loading so scopes list is available everywhere ownership checks run.

## Phase 4 – Documentation & Operator Enablement
- Update `deploy/README.md` with new Auth0 environment variables, setup steps, and troubleshooting for 401/403 errors.
- Add example curl sequences showing success/failure cases with and without proper scopes.
- Briefly document identity expectations in API reference / docs so external integrators plan for Auth0 subject binding.

## Phase 5 – Testing, Rollout, & Migration Support
- Author unit/integration tests covering valid/invalid JWTs, default-to-sub behavior, and admin override cases.
- Prepare rollout switch (feature flag or staged deploy) and define monitoring for 401/403 spikes.
- Draft optional migration playbook for legacy user IDs, including scripts and dry-run guidance.
