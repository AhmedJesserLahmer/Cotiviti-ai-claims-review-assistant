"""Shared-secret authentication between services.

Internal services (ai-agent, ml-service) must not answer arbitrary callers even
inside the cluster: a compromised pod could otherwise trigger LLM spend or re-seed the
database. Callers send ``X-Internal-Token``; the token is compared in constant time.
Probes and /metrics stay open (kubelet and Prometheus do not send it).

NetworkPolicies restrict *who can connect*; this restricts *who is allowed in*. With a
service mesh, mTLS identities would replace the shared token.
"""

from __future__ import annotations

import hmac
import json

HEADER = "x-internal-token"
OPEN_PATHS = frozenset({"/health", "/health/live", "/health/ready", "/metrics"})


class InternalAuthMiddleware:
    def __init__(self, app, token: str):
        if not token:
            raise ValueError("internal token must not be empty")
        self.app = app
        self._token = token.encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in OPEN_PATHS:
            await self.app(scope, receive, send)
            return
        presented = dict(scope.get("headers") or []).get(HEADER.encode(), b"")
        if not hmac.compare_digest(presented, self._token):
            body = json.dumps({"detail": "missing or invalid internal token"}).encode()
            headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
            await send({"type": "http.response.start", "status": 401, "headers": headers})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)


def internal_headers(token: str) -> dict[str, str]:
    return {"X-Internal-Token": token} if token else {}
