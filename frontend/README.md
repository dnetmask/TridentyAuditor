# TridentyAuditor — frontend

React + Vite + TypeScript. Consume la API del backend: motor de frameworks
(solo lectura) y MOD·DOC (control documental). Ver
[`docs/modules`](../docs/modules) en la raíz del repo para el diseño de cada
módulo.

## Correr en desarrollo

Con el backend ya corriendo (ver `../backend/README.md` o `../deploy`):

```bash
cd frontend
npm install
cp .env.example .env.local   # ajustar VITE_API_BASE_URL si el backend no está en :8000
npm run dev
```

Abre `http://localhost:5173`.

## Autenticación

No hay Keycloak todavía (Fase 2 de la hoja de ruta). La pantalla de acceso
(`/entrar`) minta un JWT de desarrollo llamando a
`POST /api/v1/dev/token` — un endpoint que **solo existe cuando el backend
corre con `TRIDENTY_ENVIRONMENT=local`**. Crear un tenant desde ahí requiere
el `X-Admin-Token` del backend (`TRIDENTY_ADMIN_BOOTSTRAP_TOKEN`).

Esto es exclusivamente para desarrollo — reemplazarlo por el flujo real
contra Keycloak/OIDC es parte de la Fase 2.

## Estructura

```
src/api/         cliente fetch + tipos que reflejan los schemas del backend
src/context/     sesión (tenant/usuario/token) persistida en localStorage
src/components/  Layout (nav) y piezas compartidas (StatusBadge)
src/pages/       LoginPage, DocumentsPage, FrameworksPage
```
