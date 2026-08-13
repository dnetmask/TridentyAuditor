# TridentyAuditor

Plataforma GRC multitenant, nativa de contenedores, para gestión documental y
seguimiento paso a paso de un Sistema de Gestión de Seguridad de la Información.

Un solo motor de frameworks que hoy habla ISO/IEC 27001:2022 y en la Fase 2
habla NIST CSF 2.0, empaquetado en contenedores OCI para desplegarse en
cualquier nube o en el centro de datos del cliente.

> Ver [`docs/architecture/tridentyauditor-arquitectura.md`](docs/architecture/tridentyauditor-arquitectura.md)
> para el documento de arquitectura completo (V0.1, borrador de discusión).

## Estado del proyecto

Fase 1 en construcción. Módulos implementados hasta ahora:

| Módulo | Código | Estado |
|---|---|---|
| Motor de frameworks | — | ✅ Esqueleto + seed ISO/IEC 27001:2022 |
| Multitenencia (tier pooled, RLS) | — | ✅ Esqueleto |
| Autenticación y roles | — | ✅ Login real (email/contraseña), Super Admin / Admin del tenant / Auditor interno / Visualizador |
| Control documental | MOD·DOC | ✅ Funcional (CRUD + versionado + aprobación + subida/descarga real de archivos) |
| Asistente paso a paso | MOD·WZD | ✅ Funcional (8 fases, evidencia obligatoria, desbloqueo por fase) |
| Gestión de riesgos | MOD·RSK | ✅ Funcional (activos, matriz probabilidad×impacto, tratamiento, residual) |
| SoA · Anexo A | MOD·SOA | ✅ Funcional (93 controles, exclusión con justificación, dueño) |
| Indicador de cumplimiento | — | ✅ % de evidencia aprobada (SoA + asistente), visible en la barra superior |
| Auditoría interna | MOD·AUD | ✅ Funcional (programa de auditoría, hallazgos clasificados, CAPA con cierre verificable) |
| Indicadores y revisión | MOD·KPI | ⏳ Fase 1, pendiente |
| Capacitación y cultura | MOD·TRN | ⏳ Fase 1, pendiente |
| Módulo NIST CSF 2.0 | MOD·NIST | ⏳ Fase 2 |
| Frontend (React) | — | ✅ Ruta SGSI, Documentos, Marco normativo, SoA, Riesgos, Auditoría |

Ver [`docs/modules/`](docs/modules) para el detalle de cada módulo.

## Estructura del repo

```
backend/            API FastAPI (motor de frameworks, tenants, MOD·DOC, MOD·WZD)
frontend/           SPA React + Vite + TypeScript
deploy/             docker-compose para desarrollo local + Helm chart
docs/architecture/  documento de arquitectura
docs/modules/       una ficha por módulo (alcance, estado, endpoints)
```

## Desarrollo local

```bash
cd deploy
docker compose up --build
```

Un solo comando, un solo puerto: esto levanta Postgres y la API en
`http://localhost:8001`, que **también sirve el frontend ya compilado** en
esa misma URL (docs interactivas en `/docs`) — sin necesidad de tener
Node/npm instalados en la máquina. `backend/Dockerfile` compila el frontend
en una etapa `node:22` y copia el resultado a `app/static/frontend`; FastAPI
lo sirve como archivos estáticos y cae a `index.html` para las rutas del
lado del cliente (React Router), así que entrar directo a una URL como
`/ruta-sgsi` o refrescar la página ahí funciona igual que con cualquier SPA.
El puerto host de la API se movió de 8000 a 8001 porque 8000 es un puerto
común y suele chocar con otro proceso/contenedor ya corriendo en la
máquina. Ver [`backend/README.md`](backend/README.md) para correr el
backend sin contenedores y ejecutar las pruebas.

Para desarrollar el frontend con hot-reload (cambios en `frontend/src` se
reflejan al vuelo, sin reconstruir nada) en vez de depender del build
estático de arriba:

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Esto agrega un servicio `frontend` aparte con el dev server de Vite en
`http://localhost:5173`, montando el código fuente como volumen. O, si ya
tienes Node instalado y prefieres correrlo fuera de Docker:

```bash
cd frontend
npm install
echo "VITE_API_BASE_URL=http://localhost:8001" > .env.local   # el backend corre con docker compose
npm run dev
```

Ver [`frontend/README.md`](frontend/README.md) para el detalle de ambos
flujos. La primera cuenta (Super Admin) se crea automáticamente al arrancar
si defines `TRIDENTY_SUPER_ADMIN_EMAIL`/`TRIDENTY_SUPER_ADMIN_PASSWORD`
antes del primer `docker compose up` (ver `deploy/docker-compose.yml`), o a
mano después con el script de bootstrap — ver
[`backend/README.md`](backend/README.md#autenticación) y
[`docs/modules/auth-roles.md`](docs/modules/auth-roles.md) para el modelo de
roles completo.
