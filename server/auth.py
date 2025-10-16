"""Authentication utilities for Auth0-backed JWT verification."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Set, Tuple

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError


class AuthError(Exception):
    """Represents a recoverable authentication failure."""

    def __init__(self, status_code: int, code: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass
class Identity:
    """Authenticated caller information."""

    sub: str
    scopes: Set[str]
    claims: Dict[str, Any]
    token: str
    jwks_cache_hit: bool


class JWKSCache:
    """Lightweight JWKS cache with TTL-bound refresh."""

    def __init__(self, jwks_url: str, ttl_seconds: int = 600) -> None:
        self.jwks_url = jwks_url
        self.ttl_seconds = ttl_seconds
        self._keys: Optional[Sequence[Dict[str, Any]]] = None
        self._expires_at: float = 0.0

    def _fetch(self) -> Sequence[Dict[str, Any]]:
        with urllib.request.urlopen(self.jwks_url, timeout=5) as response:
            payload = json.load(response)
        keys = payload.get("keys", [])
        if not isinstance(keys, list):  # pragma: no cover - defensive guard
            raise AuthError(500, "JWKS_INVALID", "JWKS payload malformed.")
        self._keys = keys
        self._expires_at = time.monotonic() + self.ttl_seconds
        return keys

    def get_keys(self) -> Tuple[Sequence[Dict[str, Any]], bool]:
        now = time.monotonic()
        if self._keys is not None and now < self._expires_at:
            return self._keys, True
        return self._fetch(), False

    def get_key(self, kid: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        keys, cache_hit = self.get_keys()
        for key in keys:
            if key.get("kid") == kid:
                return key, cache_hit
        # Cache may be stale; force refresh once
        self._keys = None
        keys, cache_hit = self.get_keys()
        for key in keys:
            if key.get("kid") == kid:
                return key, cache_hit
        return None, cache_hit


class JWTVerifier:
    """Validates Auth0-issued JWT access tokens using JWKS."""

    def __init__(
        self,
        domain: str,
        audience: str,
        algorithms: Optional[Sequence[str]] = None,
        cache_ttl_seconds: int = 600,
    ) -> None:
        if not domain or not audience:
            raise ValueError("Both domain and audience are required for JWT verification.")
        issuer = domain.rstrip("/")
        if not issuer.startswith("http://") and not issuer.startswith("https://"):
            issuer = f"https://{issuer}"
        self.issuer = issuer.rstrip("/") + "/"
        self.audience = audience
        self.algorithms = tuple(algorithms or ("RS256",))
        self.jwks_cache = JWKSCache(f"{self.issuer}.well-known/jwks.json", ttl_seconds=cache_ttl_seconds)

    def verify_authorization_header(self, authorization: Optional[str]) -> Identity:
        if not authorization:
            raise AuthError(401, "AUTH_HEADER_MISSING", "Authorization header missing.")
        scheme, _, token = authorization.partition(" ")
        if not token:
            raise AuthError(401, "AUTH_TOKEN_MISSING", "Authorization header is malformed.")
        if scheme.lower() != "bearer":
            raise AuthError(401, "AUTH_SCHEME_INVALID", "Authorization scheme must be Bearer.")
        return self.verify_token(token)

    def verify_token(self, token: str) -> Identity:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise AuthError(401, "TOKEN_INVALID", "Unable to parse JWT header.") from exc

        kid = unverified_header.get("kid")
        if not kid:
            raise AuthError(401, "TOKEN_KID_MISSING", "JWT is missing a key identifier (kid) header.")

        jwk_key, cache_hit = self.jwks_cache.get_key(kid)
        if not jwk_key:
            raise AuthError(401, "TOKEN_KID_UNKNOWN", "Signing key not found for token.", {"kid": kid})

        try:
            claims = jwt.decode(
                token,
                jwk_key,
                algorithms=list(self.algorithms),
                audience=self.audience,
                issuer=self.issuer,
            )
        except ExpiredSignatureError as exc:
            raise AuthError(401, "TOKEN_EXPIRED", "JWT has expired.") from exc
        except JWTClaimsError as exc:
            raise AuthError(401, "TOKEN_CLAIMS_INVALID", "JWT claims validation failed.", {"detail": str(exc)}) from exc
        except JWTError as exc:
            raise AuthError(401, "TOKEN_INVALID", "JWT verification failed.", {"detail": str(exc)}) from exc

        subject = claims.get("sub")
        if not subject:
            raise AuthError(401, "TOKEN_SUB_MISSING", "JWT subject (sub) claim is required.")

        scopes = self._extract_scopes(claims)
        return Identity(sub=subject, scopes=scopes, claims=claims, token=token, jwks_cache_hit=cache_hit)

    @staticmethod
    def _extract_scopes(claims: Dict[str, Any]) -> Set[str]:
        scopes: Set[str] = set()
        scope_claim = claims.get("scope")
        if isinstance(scope_claim, str):
            scopes.update(part for part in scope_claim.split() if part)
        permissions_claim = claims.get("permissions")
        if isinstance(permissions_claim, (list, tuple)):
            scopes.update(str(item) for item in permissions_claim if isinstance(item, str))
        return scopes


__all__ = ["AuthError", "Identity", "JWTVerifier"]
