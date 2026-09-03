# MOD·LEG — Matriz de requisitos legales

**Fase:** LG (agregada a la ruta tras el análisis comparativo con Kawak) ·
**Estado:** ✅ Implementado (`backend/app/legal`)

Registro estructurado de los requisitos legales, estatutarios, regulatorios y
contractuales que aplican al tenant — lo que ISO 27001 exige en la cláusula 4
(contexto de la organización) y en el control **A.5.31**. Para tenants
CNO-1960 cumple el mismo papel con el marco regulatorio del sector eléctrico
(Acuerdo 1960, resoluciones CREG, Ley 1581, Ley 1273, …).

## Modelo

**LegalRequirement** — por tenant, con RLS (mismo plano de datos que
`Asset`/`Area`); nombre único por tenant:

| Campo | Qué guarda |
|---|---|
| `requirement_type` | constitución, ley, decreto, resolución, circular, norma/estándar, contrato, guía u otro |
| `name`, `issuer`, `publication_year`, `articles` | identidad del requisito ("Ley 1581 de 2012", Congreso, 2012, "Toda la ley") |
| `description`, `topic` | qué regula y el tema (ej. protección de datos personales) |
| `responsible_user_id` | responsable — usuario activo del mismo tenant (validación manual: `users` no tiene RLS) |
| `evidence_document_id` + `application_evidence` | CÓMO se cumple: documento de MOD·DOC vinculado (mismo patrón de evidencia del SoA/riesgos) + descripción libre |
| `review_frequency_months`, `next_review_date` | revisión programada con el mismo semáforo de MOD·DOC |
| `expiration_date` | vencimiento del requisito en sí (contratos, permisos); NULL = no vence |
| `status` | `in_force` (vigente) / `repealed` (derogado — deja de contar) |
| `compliance_rating` | calificación: sin evaluar / cumple / parcial / no cumple |

## Nivel de cumplimiento

`GET /api/v1/legal-requirements/summary` calcula, **solo sobre requisitos
vigentes**: `(cumple + 0.5 × parcial) / total`. Una matriz vacía no es "0%"
— es "sin levantar", y por eso el componente no aparece en el indicador
global hasta que exista el primer requisito.

**Indicador global**: cuando el tenant tiene matriz, el % de la barra
superior pasa de `SoA 60% + asistente 40%` a `SoA 50% + asistente 30% +
requisitos legales 20%` (ver `app/compliance/service.py`).

## Endpoints

Todos requieren `Authorization: Bearer <jwt>` de un usuario del tenant.
Escriben Admin del tenant y Auditor interno; lee cualquier rol.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/legal-requirements/summary` | Nivel de cumplimiento (solo vigentes) |
| POST | `/api/v1/legal-requirements` | Crea un requisito (409 si el nombre ya existe) |
| GET | `/api/v1/legal-requirements` | Lista la matriz del tenant |
| PATCH | `/api/v1/legal-requirements/{id}` | Edición parcial: metadatos, responsable, evidencia, calificación, estado |

No hay DELETE — igual que en MOD·DOC, un requisito que dejó de aplicar se
marca `repealed` y queda como registro histórico. Crear y actualizar quedan
en la [bitácora de auditoría](activity-log.md) (`legal.created`,
`legal.updated`).

## Frontend

Página **Requisitos legales** (`/requisitos-legales`): tabla con tipo,
requisito (nombre + emisor · año), tema, responsable, próxima revisión con
semáforo y calificación editable inline; filtros por texto/tipo/estado/
calificación (por defecto solo vigentes); "Nivel de cumplimiento: N%" en el
encabezado; detalle expandible con artículos, descripción, evidencia
vinculada y acciones (editar, marcar derogado/reactivar). El selector de
evidencia solo ofrece documentos vigentes con versión aprobada — el mismo
criterio del resto de módulos.

## Pendiente

- Registros estructurados de las otras dos piezas de la cláusula 4 (análisis
  de contexto y partes interesadas) — hoy se cubren como tareas con evidencia
  en la ruta paso a paso.
- Recordatorios de revisión/vencimiento por correo (hoy el semáforo es
  visual) — junto con los de MOD·DOC, Fase 3 de la ruta.
