import time

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from claims_common.auth import AuthSettings, build_auth

SECRET = "s" * 40


def token(**claims):
    payload = {"sub": "user-1", "exp": int(time.time()) + 300, "roles": ["reviewer"], **claims}
    return jwt.encode(payload, SECRET, algorithm="HS256")


def make(**settings):
    auth = AuthSettings(_env_file=None, auth_enabled=True, jwt_secret=SECRET, **settings)
    get_principal, require_roles = build_auth(auth)
    app = FastAPI()

    @app.get("/me")
    async def me(principal=Depends(get_principal)):
        return {"sub": principal.subject, "roles": sorted(principal.roles)}

    @app.post("/admin", dependencies=[Depends(require_roles("admin"))])
    async def admin():
        return {"ok": True}

    return TestClient(app)


def bearer(value):
    return {"Authorization": f"Bearer {value}"}


def test_valid_token_yields_principal():
    body = make().get("/me", headers=bearer(token())).json()
    assert body == {"sub": "user-1", "roles": ["reviewer"]}


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Basic abc"}, bearer("not-a-jwt"), bearer(jwt.encode({"sub": "x", "exp": 9e9}, "wrong" * 10, algorithm="HS256"))],
)
def test_missing_or_invalid_tokens_are_rejected(headers):
    r = make().get("/me", headers=headers)
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_expired_token_and_issuer_audience_checks():
    c = make(jwt_issuer="https://idp", jwt_audience="claims-api", jwt_leeway_s=0)
    assert c.get("/me", headers=bearer(token(exp=int(time.time()) - 10, iss="https://idp", aud="claims-api"))).json()["detail"] == "Token expired"
    assert c.get("/me", headers=bearer(token(iss="https://evil", aud="claims-api"))).status_code == 401
    assert c.get("/me", headers=bearer(token(iss="https://idp", aud="other"))).status_code == 401
    assert c.get("/me", headers=bearer(token(iss="https://idp", aud="claims-api"))).status_code == 200


def test_roles_and_keycloak_claims():
    c = make()
    assert c.post("/admin", headers=bearer(token())).status_code == 403
    assert c.post("/admin", headers=bearer(token(roles=None, realm_access={"roles": ["admin"]}))).status_code == 200


def test_disabled_auth_is_anonymous_with_all_roles():
    get_principal, require_roles = build_auth(AuthSettings(_env_file=None, auth_enabled=False))
    app = FastAPI()

    @app.post("/admin", dependencies=[Depends(require_roles("admin"))])
    async def admin():
        return {"ok": True}

    assert TestClient(app).post("/admin").status_code == 200


def test_production_guard():
    with pytest.raises(RuntimeError, match="AUTH_ENABLED"):
        AuthSettings(_env_file=None).check_production(True)
    with pytest.raises(RuntimeError, match="32 characters"):
        AuthSettings(_env_file=None, auth_enabled=True, jwt_secret="short").check_production(True)
    AuthSettings(_env_file=None, auth_enabled=True, jwt_secret=SECRET).check_production(True)
    AuthSettings(_env_file=None).check_production(False)
