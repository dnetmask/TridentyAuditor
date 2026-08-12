# MOD·AUD — Auditoría interna

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/audit`, `frontend/src/pages/AuditPage.tsx`)

Programa de auditoría interna, hallazgos clasificados y su CAPA (causa raíz,
acción correctiva, responsable y evidencia de cierre) — el módulo que
convierte la fase 7 del ciclo del asistente ("Auditoría interna → Hallazgos y
CAPA", ver [mod-wzd.md](mod-wzd.md)) en datos estructurados, consultables y
con la misma exigencia de evidencia real que el resto de la plataforma.

## Modelo

- **AuditProgram**: una auditoría planeada o ejecutada — título, alcance,
  dominio opcional del Anexo A (`domain_id`, para auditorías acotadas como
  "Auditoría A.8 Q1 2026"), auditor asignado, fecha planeada/ejecutada y
  estado (`planned` / `in_progress` / `completed`). Plano de datos del tenant
  (RLS).
- **AuditFinding**: un hallazgo de una auditoría, con el CAPA guardado en la
  misma fila — mismo patrón que `Risk` en MOD·RSK, que guarda tratamiento y
  residual junto al riesgo en vez de en una tabla aparte. Campos: control
  relacionado (opcional), clasificación (`major_nc` / `minor_nc` /
  `observation` / `improvement`), descripción, causa raíz, acción
  correctiva, responsable, fecha de vencimiento, estado (`open` /
  `in_progress` / `closed`), evidencia de cierre y `closed_at`.

## Reglas de negocio

- **Un hallazgo cerrado exige evidencia aprobada.** `PATCH
  /api/v1/audit/findings/{id}` rechaza con 422 cualquier intento de poner
  `status=closed` sin un `evidence_document_id` que apunte a un documento de
  MOD·DOC con una versión aprobada — mismo candado que ya existe en
  MOD·WZD (`complete_task`) y reutiliza el mismo helper
  (`app/documents/service.py::has_approved_version`). Aplica a las cuatro
  clasificaciones por igual, no solo a las no conformidades: hasta una
  observación necesita algo que demuestre que se atendió.
- Reabrir un hallazgo (`status` distinto de `closed`) limpia `closed_at`
  automáticamente.
- Crear un hallazgo valida que la auditoría (`audit_id`) exista y sea del
  tenant — no se puede colgar un hallazgo de una auditoría ajena o
  inexistente (404).
- No hay una relación M2M como `RiskControlLink`: un hallazgo apunta a lo
  sumo a un control (`control_id` opcional), porque en la práctica un
  hallazgo de auditoría nace de revisar un control puntual, no de varios a
  la vez.

## Endpoints

Todos requieren `Authorization: Bearer <jwt>` de un tenant.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/audit/programs` | Crea una auditoría (`tenant_admin`, `internal_auditor`) |
| GET | `/api/v1/audit/programs` | Lista las auditorías del tenant |
| PATCH | `/api/v1/audit/programs/{id}` | Actualiza estado, fechas, auditor, dominio |
| POST | `/api/v1/audit/findings` | Crea un hallazgo bajo una auditoría |
| GET | `/api/v1/audit/findings?audit_id=` | Lista hallazgos, opcionalmente filtrados por auditoría |
| PATCH | `/api/v1/audit/findings/{id}` | Actualiza CAPA/estado/evidencia (valida el cierre) |
| GET | `/api/v1/audit/summary` | Conteos: auditorías, hallazgos por estado y por clasificación mayor/menor |

## Pendiente

- El indicador de **cumplimiento SGSI** (ver
  [compliance-indicator.md](compliance-indicator.md)) todavía no incorpora
  los hallazgos cerrados de MOD·AUD como tercera señal — queda como
  extensión futura, junto con MOD·RSK y NIST CSF 2.0.
- Sin plantillas de checklist por dominio (la sección 05 del documento de
  arquitectura menciona "checklists por dominio"); hoy el auditor redacta el
  alcance libremente en texto.
- Un hallazgo solo puede vincularse a un control; si en la práctica hace
  falta cubrir varios controles desde un mismo hallazgo, tocará revisar este
  límite.
