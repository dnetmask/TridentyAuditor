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
| Control documental | MOD·DOC | ✅ Funcional (CRUD + versionado + aprobación) |
| Gestión de riesgos | MOD·RSK | ⏳ Fase 1, pendiente |
| SoA · Anexo A | MOD·SOA | ⏳ Fase 1, pendiente |
| Auditoría interna | MOD·AUD | ⏳ Fase 1, pendiente |
| Asistente paso a paso | MOD·WZD | ⏳ Fase 1, pendiente |
| Indicadores y revisión | MOD·KPI | ⏳ Fase 1, pendiente |
| Capacitación y cultura | MOD·TRN | ⏳ Fase 1, pendiente |
| Módulo NIST CSF 2.0 | MOD·NIST | ⏳ Fase 2 |

Ver [`docs/modules/`](docs/modules) para el detalle de cada módulo.

## Estructura del repo

```
backend/            API FastAPI (motor de frameworks, tenants, MOD·DOC)
deploy/             docker-compose para desarrollo local + Helm chart
docs/architecture/  documento de arquitectura
docs/modules/       una ficha por módulo (alcance, estado, endpoints)
```

## Desarrollo local

```bash
cd deploy
docker compose up --build
```

Esto levanta Postgres y la API en `http://localhost:8000` (docs interactivas en
`/docs`). Ver [`backend/README.md`](backend/README.md) para correr el backend
sin contenedores y ejecutar las pruebas.
