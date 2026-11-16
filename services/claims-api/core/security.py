"""Authentication for claims-api (JWT bearer tokens from the identity provider)."""

from claims_common.auth import AuthSettings, Principal, build_auth
from core.config import settings

auth_settings = AuthSettings()
auth_settings.check_production(settings.is_production)

get_principal, require_roles = build_auth(auth_settings)

__all__ = ["Principal", "auth_settings", "get_principal", "require_roles"]
