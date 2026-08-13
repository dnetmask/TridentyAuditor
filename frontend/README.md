# TridentyAuditor — frontend

React + Vite + TypeScript. Consume la API del backend: motor de frameworks
(solo lectura), MOD·DOC (control documental), MOD·WZD (asistente paso a
paso) y autenticación/roles. Ver [`docs/modules`](../docs/modules) en la
raíz del repo para el diseño de cada módulo.

## Correr en desarrollo

**Con Docker, sin tocar nada (no requiere Node/npm instalados):**
`cd ../deploy && docker compose up --build` compila este frontend dentro de
`backend/Dockerfile` (etapa `node:22`) y lo sirve en
`http://localhost:8001`, el mismo puerto que la API — ver
[`../backend/README.md`](../backend/README.md). Para tocar el frontend hace
falta el flujo de abajo con hot-reload; este modo por sí solo no recarga
cambios de `src/`.

**Con Docker + hot-reload** (recompila al vuelo cada cambio en `src/`, sin
reconstruir ninguna imagen):

```bash
cd ../deploy
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Esto agrega un servicio `frontend` aparte (dev server de Vite) en
`http://localhost:5173`, con el código fuente montado como volumen.

**Sin Docker**, con el backend ya corriendo (ver `../backend/README.md` o
`../deploy`):

```bash
cd frontend
npm install
cp .env.example .env.local   # backend sin contenedores -> :8000 (default); con docker compose -> :8001
npm run dev
```

Abre `http://localhost:5173`.

## Autenticación y roles

Login real con email/contraseña contra `POST /api/v1/auth/login` — no hay
Keycloak todavía (Fase 2 de la hoja de ruta), pero ya no hay atajos sin
credenciales. Para tener con qué entrar, crea primero un Super Admin desde
el backend — por variable de entorno al arrancar o con
`python scripts/create_super_admin.py` (ver `backend/README.md#autenticación`)
— y sigue el flujo desde la UI:

1. Entra como Super Admin → `/admin/tenants` → **+ Nuevo tenant** → el
   formulario pide crear de una vez el primer **Admin del tenant**.
2. Entra como ese Admin del tenant → `/usuarios` → crea cuentas de
   **Auditor interno** y **Visualizador** para el resto del equipo.

La navegación y los botones de escritura (crear documento, aprobar,
completar tareas del wizard, instanciar el ciclo SGSI) se muestran u
ocultan según el rol de la sesión — ver [`docs/modules/auth-roles.md`](../docs/modules/auth-roles.md)
para la matriz completa. Es una ayuda de UX, no el control de acceso real:
el backend aplica las mismas reglas en cada endpoint aunque la UI no las
muestre.

## Estructura

```
src/api/         cliente fetch + tipos que reflejan los schemas del backend
src/context/     sesión (usuario/tenant/rol/token) persistida en localStorage
src/components/  Layout (nav por rol) y piezas compartidas (StatusBadge)
src/pages/       LoginPage, AdminTenantsPage, UsersPage,
                 WizardPage, DocumentsPage, FrameworksPage
```
