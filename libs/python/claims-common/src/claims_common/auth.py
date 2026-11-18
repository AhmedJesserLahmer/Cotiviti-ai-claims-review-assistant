"""Bearer-token (JWT) authentication and role-based authorization.

Tokens are issued by the organization's identity provider (OIDC); services only
verify them. Supported keys: a shared HS256 secret (``JWT_SECRET``) or an RS256/ES256
public key (``JWT_PUBLIC_KEY``, PEM). ``iss``, ``aud`` and ``exp`` are always checked
when configured.

Roles are read from the ``roles`` claim (list) or Keycloak-style
``realm_access.roles``. When auth is disabled (local development only), requests run
as an anonymous principal holding every role; production settings refuse to start in
that state (see ``AuthSettings.check_production``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastapi import Depends, HTTPException, Request
from pydantic_settings import BaseSettings, SettingsConfigDict

ALL_ROLES = frozenset({"reviewer", "admin"})


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    auth_enabled: bool = False
    jwt_secret: str = ""
    jwt_public_key: str = ""
    jwt_algorithms: str = "HS256,RS256,ES256"
    jwt_issuer: str = ""
    jwt_audience: str = ""
    jwt_leeway_s: int = 30

    @property
    def algorithms(self) -> list[str]:
        return [a.strip() for a in self.jwt_algorithms.split(",") if a.strip()]

    @property
    def verification_key(self) -> str:
        return self.jwt_public_key or self.jwt_secret

    def check_production(self, is_production: bool) -> None:
        if not is_production:
            return
        if not self.auth_enabled:
            raise RuntimeError("AUTH_ENABLED must be true when ENVIRONMENT=prod")
        if not self.verification_key:
            raise RuntimeError("JWT_SECRET or JWT_PUBLIC_KEY is required when auth is enabled")
        if self.jwt_secret and len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters")


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    claims: dict[str, Any] = field(default_factory=dict)
    authenticated: bool = True

    def has_any(self, *roles: str) -> bool:
        return bool(self.roles & set(roles))


ANONYMOUS = Principal(subject="anonymous", roles=ALL_ROLES, authenticated=False)


def _roles_from(claims: dict[str, Any]) -> frozenset[str]:
    roles = claims.get("roles") or (claims.get("realm_access") or {}).get("roles") or []
    if isinstance(roles, str):
        roles = roles.split()
    return frozenset(str(r) for r in roles)


def decode_token(token: str, settings: AuthSettings) -> Principal:
    import jwt

    options = {"require": ["exp", "sub"]}
    try:
        claims = jwt.decode(
            token,
            settings.verification_key,
            algorithms=settings.algorithms,
            audience=settings.jwt_audience or None,
            issuer=settings.jwt_issuer or None,
            leeway=settings.jwt_leeway_s,
            options={**options, "verify_aud": bool(settings.jwt_audience)},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"}) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"}
        ) from exc
    return Principal(subject=str(claims["sub"]), roles=_roles_from(claims), claims=claims)


def build_auth(settings: AuthSettings):
    """Return (get_principal, require_roles) FastAPI dependencies bound to ``settings``."""

    async def get_principal(request: Request) -> Principal:
        if not settings.auth_enabled:
            return ANONYMOUS
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=401, detail="Missing bearer token", headers={"WWW-Authenticate": "Bearer"}
            )
        principal = decode_token(token.strip(), settings)
        request.state.principal = principal
        return principal

    def require_roles(*roles: str):
        async def dependency(principal: Principal = Depends(get_principal)) -> Principal:
            if not principal.has_any(*roles):
                raise HTTPException(status_code=403, detail=f"Requires role: {' or '.join(roles)}")
            return principal

        return dependency

    return get_principal, require_roles
