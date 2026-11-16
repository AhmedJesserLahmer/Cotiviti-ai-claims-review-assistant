from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logging import RequestContextMiddleware, configure_logging
from routers import claims, health, providers, seed

configure_logging()

app = FastAPI(title="Claims Review Assistant POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
# Added last so it wraps everything, including CORS preflight responses.
app.add_middleware(RequestContextMiddleware)

app.include_router(health.router)
app.include_router(seed.router)
app.include_router(claims.router)
app.include_router(providers.router)
