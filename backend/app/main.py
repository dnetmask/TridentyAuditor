from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import SessionLocal
from app.documents.router import router as documents_router
from app.frameworks.router import controls_router, domains_router
from app.frameworks.router import router as frameworks_router
from app.frameworks.seeds.iso27001_2022 import seed_iso27001
from app.tenants.router import router as tenants_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = SessionLocal()
    try:
        seed_iso27001(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="TridentyAuditor",
    description=(
        "Plataforma GRC multitenant — motor de frameworks, multitenencia y "
        "MOD·DOC (control documental). Ver /docs/architecture en el repo."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(frameworks_router)
app.include_router(domains_router)
app.include_router(controls_router)
app.include_router(tenants_router)
app.include_router(documents_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
