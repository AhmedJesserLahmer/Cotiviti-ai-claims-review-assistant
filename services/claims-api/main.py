from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import claims, providers, seed

app = FastAPI(title="Claims Review Assistant POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(seed.router)
app.include_router(claims.router)
app.include_router(providers.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
