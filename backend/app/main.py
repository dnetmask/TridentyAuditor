from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.activity.router import router as activity_router
from app.areas.router import router as areas_router
from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.auth.service import bootstrap_super_admin
from app.compliance.router import router as compliance_router
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.documents.router import router as documents_router
from app.frameworks.router import controls_router, domains_router
from app.frameworks.router import router as frameworks_router
from app.frameworks.seeds.cno1960 import seed_cno1960
from app.frameworks.seeds.iso27001_2022 import seed_iso27001
from app.legal.router import router as legal_router
from app.risk.router import router as risk_router
from app.soa.router import router as soa_router
from app.tenants.router import router as tenants_router
from app.wizard.router import router as wizard_router
from app.wizard.seeds.cno_route import seed_cno_route
from app.wizard.seeds.methodology import seed_wizard_phases

STATIC_DIR = Path(__file__).parent / "static"
FRONTEND_DIR = Path(__file__).parent / "static" / "frontend"
settings = get_settings()


class SPAStaticFiles(StaticFiles):
    """Sirve el build de React y cae a index.html para rutas del lado del
    cliente (React Router) — ej. entrar directo a /ruta-sgsi o refrescar la
    página ahí debe servir la SPA, no un 404, para que el router del
    navegador tome el control. No aplica a /api/... : una ruta de API
    desconocida debe seguir devolviendo 404, no HTML.
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aborta el arranque si la configuración es insegura fuera de local
    # (secreto JWT default, CORS sin https) — Fase S1.
    settings.assert_production_ready()
    db = SessionLocal()
    try:
        seed_iso27001(db)
        seed_cno1960(db)
        seed_wizard_phases(db)
        seed_cno_route(db)
        bootstrap_super_admin(
            db,
            email=settings.super_admin_email,
            password=settings.super_admin_password,
            full_name=settings.super_admin_name,
        )
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

_MAX_BODY_BYTES = settings.max_request_body_mb * 1024 * 1024

# CSP para la SPA que la propia API sirve. script-src 'self' (el build de
# Vite emite solo <script src>); /docs necesita el script inline que genera
# get_swagger_ui_html, por eso lleva su propia variante. style-src permite
# inline porque React aplica estilos vía atributo style.
_CSP_APP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
    "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
)
_CSP_DOCS = _CSP_APP.replace("script-src 'self'", "script-src 'self' 'unsafe-inline'")


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Cabeceras de seguridad en toda respuesta + tope de tamaño de request.

    El tope por Content-Length frena a los clientes honestos con cuerpos
    gigantes antes de leerlos; los cuerpos chunked sin Content-Length los
    cortan los endpoints de subida (lectura por chunks con límite) y el
    ingress en producción.
    """
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > _MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"El cuerpo supera el máximo de {settings.max_request_body_mb} MB"},
        )

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        _CSP_DOCS if request.url.path.startswith("/docs") else _CSP_APP
    )
    if not settings.is_local:
        # Solo tiene sentido detrás de TLS — y fuera de local, TLS es requisito.
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sin esto el navegador oculta este header a fetch() en peticiones
    # cross-origin — el nombre real del archivo nunca llegaría al cliente en
    # desarrollo (frontend :5173, API :8000); en producción el frontend se
    # sirve desde el mismo origen que la API (ver SPAStaticFiles) así que ahí
    # no haría falta, pero también se necesita para dev con Vite.
    expose_headers=["Content-Disposition"],
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


app.include_router(auth_router)
app.include_router(frameworks_router)
app.include_router(domains_router)
app.include_router(controls_router)
app.include_router(tenants_router)
app.include_router(areas_router)
app.include_router(documents_router)
app.include_router(legal_router)
app.include_router(wizard_router)
app.include_router(soa_router)
app.include_router(risk_router)
app.include_router(compliance_router)
app.include_router(audit_router)
app.include_router(activity_router)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# Registrado al final a propósito: Starlette evalúa las rutas en orden de
# registro, así que este mount en "/" solo recibe lo que ninguna ruta de
# API/Docs/estáticos anterior haya reclamado ya. Si el build del frontend no
# se copió a la imagen (ej. corriendo el backend solo, en desarrollo nativo),
# el directorio no existe y se omite sin romper el resto de la API.
if FRONTEND_DIR.is_dir():
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
