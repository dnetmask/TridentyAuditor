# MOD·SOA — SoA · Anexo A

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/soa`, `frontend/src/pages/SoaPage.tsx`)

Declaración de Aplicabilidad sobre los 93 controles de ISO/IEC 27001:2022 en
4 temas, con justificación de exclusión y dueño por control. Se construye
como una capa de aplicabilidad por tenant sobre el motor de frameworks (los
controles en sí son datos globales, no por tenant — ver
[frameworks-engine.md](frameworks-engine.md)).

## Modelo

- **SoaEntry**: una fila por tenant × control (`UniqueConstraint(tenant_id,
  control_id)`), con RLS. Se crea vía `POST /api/v1/soa/instantiate`
  (idempotente — solo agrega las entradas de controles que aún no tengan
  fila, así el catálogo puede crecer sin duplicar nada).
- Campos: `is_applicable` (default `true`), `justification`,
  `implementation_status` (`not_started`/`in_progress`/`implemented`),
  `owner_user_id` (FK a `users`, cualquier rol del tenant vía
  `GET /api/v1/auth/directory`), `evidence_document_id` (FK a `documents`),
  `notes`.

## Reglas de negocio

- **Un control excluido requiere justificación.** `PATCH
  /api/v1/soa/entries/{id}` rechaza con 422 cualquier intento de poner
  `is_applicable=false` sin una `justification` no vacía en la misma
  petición o ya guardada. Esto es lo que hace que el SoA sea defendible en
  auditoría — no se puede "desmarcar y ya".
- El frontend refleja esta regla sin pelear con el usuario: desmarcar
  "Aplicable" no dispara la petición de inmediato (eso produciría el 422
  descrito arriba); solo abre el campo de justificación de forma optimista
  en el estado local del componente, y la exclusión se confirma contra el
  backend cuando el campo pierde el foco con texto no vacío.
- El resumen (`GET /api/v1/soa/summary`) cuenta aplicables/excluidos y el
  desglose de `implementation_status` — es la fuente de los números que
  también alimentan la vista de progreso.

## Endpoints

Todos requieren `Authorization: Bearer <jwt>` de un tenant.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/soa/instantiate` | Crea las entradas del tenant a partir de los controles del framework (solo `tenant_admin`) |
| GET | `/api/v1/soa/entries` | Lista las entradas con su control y dominio anidados |
| GET | `/api/v1/soa/summary` | Conteos de aplicabilidad e implementación |
| PATCH | `/api/v1/soa/entries/{id}` | Actualiza aplicabilidad/justificación/estado/dueño (`tenant_admin`, `internal_auditor`) |

## Pendiente

- Solo cubre ISO/IEC 27001:2022 (`framework_code` fijo en el instantiate);
  cuando se agregue NIST CSF 2.0 habrá que decidir si el SoA es por
  framework o unificado.
- Sin exportación a PDF/Excel del documento SoA formal — hoy es una tabla
  viva, no un artefacto descargable.
- `evidence_document_id` existe en el modelo pero la UI todavía no lo
  expone (a diferencia de MOD·RSK, que sí lo hace en el detalle del riesgo).
