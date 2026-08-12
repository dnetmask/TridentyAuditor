from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import SessionLocal
from app.documents.router import router as documents_router
from app.frameworks.router import controls_router, domains_router
from app.frameworks.router import router as frameworks_router
from app.frameworks.seeds.iso27001_2022 import seed_iso27001
from app.tenants.router import router as tenants_router

STATIC_DIR = Path(__file__).parent / "static"


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
    docs_url=None,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/docs", include_in_schema=False)
def swagger_ui() -> HTMLResponse:
    """Docs interactivas servidas desde assets locales, no desde un CDN.

    Evita que el navegador del auditor/cliente cargue JS de un tercero
    (jsdelivr) al abrir la documentación de una plataforma de cumplimiento —
    también hace que /docs funcione sin salida a internet en despliegues
    on-prem/air-gapped (sección 05 del documento de arquitectura).
    """
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon-32x32.png",
    )


app.include_router(frameworks_router)
app.include_router(domains_router)
app.include_router(controls_router)
app.include_router(tenants_router)
app.include_router(documents_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
