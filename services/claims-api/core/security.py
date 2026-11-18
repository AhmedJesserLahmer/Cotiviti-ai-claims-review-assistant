"""Authentication for claims-api (JWT bearer tokens from the identity provider)."""

from claims_common.auth import AuthSettings, Principal, build_auth
from core.config import settings

auth_settings = AuthSettings()
auth_settings.check_production(settings.is_production)

get_principal, require_roles = build_auth(auth_settings)

# Role model:
#   reviewer  read claims/providers, run analyses, give feedback, upload claims, run jobs
#   admin     everything a reviewer can do, plus re-seeding the dataset
reviewer = require_roles("reviewer", "admin")
admin = require_roles("admin")

__all__ = ["Principal", "admin", "auth_settings", "get_principal", "require_roles", "reviewer"]
