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

## Autenticación en desarrollo

No hay integración con Keycloak todavía (llega en la Fase 2 de la hoja de
ruta). Los endpoints de MOD·DOC esperan un JWT HS256 con claims `tenant_id`,
`sub` y `role`. Para generar uno de prueba:

```bash
python scripts/make_dev_token.py <tenant-uuid> --sub tester@netmask.co --role tenant_admin
```

Los endpoints de `/api/v1/tenants` están protegidos con un token simple de
bootstrap (`X-Admin-Token`, ver `.env.example`) hasta que el rol Super Admin
Netmask se valide contra Keycloak.

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
fija ese valor por request.
