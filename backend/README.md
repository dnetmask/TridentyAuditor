# TridentyAuditor — backend

FastAPI + SQLAlchemy. Implementa el motor de frameworks (Dominio → Control →
Requisito), el modelo de tenants y MOD·DOC (control documental). Ver
[`docs/architecture`](../docs/architecture) y [`docs/modules`](../docs/modules)
en la raíz del repo para el diseño completo.

## Correr con Docker Compose (recomendado)

```bash
cd ../deploy
docker compose up --build
```

API en `http://localhost:8000`, docs interactivas en `http://localhost:8000/docs`.
El Swagger UI se sirve desde assets locales (`app/static/swagger-ui`, vendorizados
de `swagger-ui-dist`), no desde un CDN — funciona sin salida a internet, algo
relevante para el tier aislado on-prem/air-gapped de la sección 04.

## Correr localmente sin contenedores

Requiere Postgres 15+ corriendo y accesible.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # ajustar TRIDENTY_DATABASE_URL si aplica
alembic upgrade head
uvicorn app.main:app --reload
```

## Autenticación

Login real con email/contraseña (bcrypt) — no hay integración con Keycloak
todavía (llega en la Fase 2 de la hoja de ruta), pero ya no hay forma de
mintar un token sin credenciales. Ver
[`docs/modules/auth-roles.md`](../docs/modules/auth-roles.md) para el
modelo completo de roles (Super Admin, Admin del tenant, Auditor interno,
Visualizador).

La primera cuenta hay que crearla directamente en la base de datos (no
existe todavía nadie que pueda llamar a `POST /api/v1/auth/users`):

```bash
python scripts/create_super_admin.py admin@netmask.co --name "Nombre Apellido"
```

Con esa cuenta: `POST /api/v1/auth/login` → usa el `access_token` para crear
tenants (`POST /api/v1/tenants`) y el primer Admin de cada uno
(`POST /api/v1/auth/users` con `role: tenant_admin`). Cada Admin del tenant
gestiona desde ahí a sus propios Auditores internos y Visualizadores.

## Pruebas

```bash
pytest
```

Las pruebas necesitan Postgres (usan RLS real, no se simula con SQLite).
Exporta `TRIDENTY_DATABASE_URL` apuntando a una base de pruebas o usa
`docker compose -f ../deploy/docker-compose.yml up -d db` primero.

## Migraciones

```bash
alembic revision -m "descripción"   # nueva migración
alembic upgrade head                # aplicar
```

La migración `0001_initial_schema` crea el motor de frameworks, `tenants` y
MOD·DOC, y habilita Row-Level Security (`FORCE ROW LEVEL SECURITY` +
`CREATE POLICY`) sobre `documents` y `document_versions`, filtrando por
`current_setting('app.tenant_id')`. Ver `app/core/database.py` para cómo se
fija ese valor por request. `0002_wizard_module` agrega MOD·WZD (misma
técnica de RLS sobre `tenant_wizard_tasks`) y `0003_auth_users` agrega
`users` — sin RLS, vive en el plano de control como `tenants`.
