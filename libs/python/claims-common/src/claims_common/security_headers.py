"""Security headers for JSON APIs (OWASP Secure Headers Project).

APIs return claim and patient-related data, so responses must not be cached by
intermediaries, sniffed as HTML, framed, or leak referrers. HSTS is only sent in
production (TLS terminates at the ingress there).
"""

from __future__ import annotations

BASE_HEADERS = {
    b"x-content-type-options": b"nosniff",
    b"x-frame-options": b"DENY",
    b"referrer-policy": b"no-referrer",
    b"cross-origin-resource-policy": b"same-site",
    b"permissions-policy": b"camera=(), microphone=(), geolocation=()",
    # JSON APIs never need to load anything.
    b"content-security-policy": b"default-src 'none'; frame-ancestors 'none'",
}
NO_STORE = (b"cache-control", b"no-store")
HSTS = (b"strict-transport-security", b"max-age=63072000; includeSubDomains")
# Interactive docs load Swagger UI assets, so they keep a relaxed CSP.
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware:
    def __init__(self, app, *, hsts: bool = False):
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = scope.get("path", "").startswith(DOCS_PATHS)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {name.lower() for name, _ in headers}
                for name, value in BASE_HEADERS.items():
                    if name not in present and not (is_docs and name == b"content-security-policy"):
                        headers.append((name, value))
                if NO_STORE[0] not in present:
                    headers.append(NO_STORE)
                if self.hsts:
                    headers.append(HSTS)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
