# MOD·DOC — Control documental

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/documents`, `backend/app/areas`)

Versionado y flujo de aprobación de documentos, con RLS por tenant. Base
sobre la que cuelga la evidencia de los demás módulos (MOD·RSK, MOD·SOA,
MOD·AUD, MOD·WZD). Desde la Fase 1 de la ruta incluye clasificación
(área responsable + controles vinculados), fechas de ciclo de vida
(implementación / revisión programada), origen interno/externo,
numeración automática y derogación formal.

## Modelo

- **Document**: identidad estable de un documento — código, título, tipo,
  retención, y desde Fase 1:
  - `area_id` → **Area**: el área encargada del documento, proceso o
    control documentado (decisión de diseño: se modela *área*, no *sede*).
  - `implementation_date`, `review_frequency_months`, `next_review_date`:
    ciclo de revisión programada. Al aprobar una versión, si hay
    frecuencia definida, `next_review_date` se recalcula a
    `hoy + frecuencia` (meses de calendario reales).
  - `origin` (`internal`/`external`) + `external_source`: documentos de
    origen externo (normas, contratos, guías de terceros) declaran su
    fuente; al volver a `internal` la fuente se limpia.
  - `retired_at` / `retired_by` / `retirement_reason`: derogación formal
    (ver abajo).
  - **DocumentControlLink** (M2M): un documento puede evidenciar varios
    controles del framework del tenant (antes era un solo `control_id`).
    El PATCH recibe `control_ids` con semántica de reemplazo del conjunto.
- **Area**: catálogo por tenant (nombre único por tenant, RLS), con
  `manager_user_id` opcional validado contra usuarios activos del mismo
  tenant. Router propio en `backend/app/areas`.
- **DocumentVersion**: cada versión con su ciclo de vida, el binario
  subido (`original_filename`, `content_type`, `file_size`), su hash
  `file_sha256`, el motivo de cambio `change_summary` (obligatorio al
  abrir versión ≥ 2) y, si fue rechazada, `rejected_by`/`rejected_at`/
  `rejection_reason`.

## Numeración automática

`GET /api/v1/documents/next-code` sugiere el siguiente código consecutivo
por tipo: `POL-###` (política), `PRC-###` (procedimiento), `REG-###`
(registro), `DOC-###` (otro). Es una sugerencia — el usuario puede
sobreescribir el código, y la unicidad real la garantiza la restricción
`(tenant_id, code)`.

## Derogación (retiro formal)

`POST /api/v1/documents/{id}/retire` (rol revisor) marca el documento como
derogado con motivo obligatorio. Un documento derogado:

- conserva todo su historial de versiones (evidencia inmutable),
- no admite ediciones, nuevas versiones ni transiciones de estado,
- **desaparece de los selectores de evidencia** de MOD·WZD, MOD·SOA,
  MOD·RSK y MOD·AUD, y deja de contar como "documento aprobado" para el
  indicador de cumplimiento.

## Almacenamiento del binario e integridad

Cada versión exige adjuntar un archivo real. El binario se guarda en disco
local bajo `Settings.documents_storage_dir`
(`TRIDENTY_DOCUMENTS_STORAGE_DIR`), en la ruta
`{tenant_id}/{document_id}/{version_id}` (sin extensión — el nombre
original solo se conserva como metadato para la descarga, así que no hay
superficie de path traversal que sanear). En `deploy/docker-compose.yml`
vive en el volumen `tridenty_documents` — sobrevive a `docker compose
down` pero no a un `-v`.

Al subir se calcula el **SHA-256** del contenido y se persiste en la
versión. Cada descarga re-verifica el hash contra el archivo en disco: si
no coincide (archivo alterado o corrupto), la descarga se rechaza con 500
"integridad comprometida" y queda el evento en la bitácora — el binario
servido siempre es exactamente el que se aprobó.

Es almacenamiento local, coherente con el tier on-prem/air-gapped de la
sección 04 (funciona sin ningún servicio externo). Migrar a Object Storage
S3-compatible con política WORM — para HA multi-réplica y retención
inmutable de verdad — sigue pendiente como hardening de producción.

## Flujo de aprobación (copias controladas)

```
   draft ──submit──▶ in_review ──approve──▶ approved
     ▲                    │                     │
     └──────reject────────┘         (aprobar otra versión
        (motivo obligatorio)         marca esta como)
                                             ▼
                                         obsolete
```

- Solo puede haber una versión en `draft`/`in_review` a la vez por documento
  — hay que resolverla antes de abrir otra.
- Al aprobar una versión, cualquier versión previamente `approved` del mismo
  documento pasa a `obsolete` automáticamente (una sola copia vigente), y se
  recalcula `next_review_date` si el documento tiene frecuencia de revisión.
- Rechazar exige un motivo, que queda en la versión
  (`rejection_reason`) y en la bitácora.
- No existe endpoint para editar o borrar una versión `approved` — es
  intencional: sección 06 del documento de arquitectura exige evidencia
  inmutable una vez publicada.

## Endpoints

Todos requieren `Authorization: Bearer <jwt>`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/documents/next-code?document_type=` | Sugiere el siguiente código consecutivo por tipo |
| POST | `/api/v1/documents` | `multipart/form-data` — crea documento + versión 1 en `draft` (código, título, tipo, área, controles, origen, fechas, retención + archivo) |
| GET | `/api/v1/documents` | Lista documentos del tenant (incluye derogados — el filtrado de vigencia es del cliente) |
| GET | `/api/v1/documents/{id}` | Detalle con área, controles y todas sus versiones |
| PATCH | `/api/v1/documents/{id}` | Edita metadatos (título, área, `control_ids` como reemplazo del conjunto, origen/fuente, fechas, frecuencia, retención). Bloqueado si el documento está derogado |
| POST | `/api/v1/documents/{id}/retire` | Deroga el documento con motivo obligatorio (rol revisor) |
| POST | `/api/v1/documents/{id}/versions` | `multipart/form-data` — nueva versión en `draft` con `change_summary` obligatorio |
| GET | `/api/v1/documents/{id}/versions/{n}/file` | Descarga el binario (verifica SHA-256 antes de servir) |
| POST | `/api/v1/documents/{id}/versions/{n}/submit` | `draft` → `in_review` |
| POST | `/api/v1/documents/{id}/versions/{n}/reject` | `in_review` → `draft`, con `reason` obligatorio |
| POST | `/api/v1/documents/{id}/versions/{n}/approve` | `in_review` → `approved` + recalcula próxima revisión |
| POST | `/api/v1/areas` | Crea un área (tenant_admin) |
| GET | `/api/v1/areas` | Lista las áreas del tenant |
| PATCH | `/api/v1/areas/{id}` | Renombra o cambia el responsable del área |

Los POST que crean documento/versión reciben `multipart/form-data` (campos
de texto vía `Form` + el archivo vía `File`), no JSON — es la única forma de
adjuntar un binario en el mismo request. Límite de tamaño configurable con
`TRIDENTY_DOCUMENTS_MAX_FILE_SIZE_MB` (25 MB por defecto).

**Subida endurecida (Fase S1):** el archivo se lee por chunks (el límite
corta antes de cargar un cuerpo gigante a memoria) y pasa por una allowlist
de tipos (`app/documents/filetypes.py`): PDF, Office, imágenes y texto
plano, con verificación de firma binaria (magic bytes) — un `.pdf` que no
empieza con `%PDF` se rechaza con 415. El `content_type` que declara el
navegador se ignora: el tipo servido en la descarga se deriva de la
extensión validada. Todo el ciclo de vida (crear, editar, enviar, aprobar,
rechazar, derogar, descargar) queda en la
[bitácora de auditoría](activity-log.md).

## Frontend

La pantalla de Documentos incluye: barra de filtros (búsqueda por
código/título, tipo, estado vigente, área y vigencia — por defecto oculta
derogados), columna de próxima revisión con semáforo (vencida en rojo,
≤30 días en ámbar), badge "Derogado", panel de detalle con chips de
controles y hash SHA-256, edición de metadatos, derogación con motivo,
sugerencia automática de código al elegir tipo, y gestión de áreas
(crear/listar con responsable) desde la misma pantalla.

## Pendiente

- Listas maestras y política de retención automatizada (hoy `retention_months`
  se guarda pero no dispara ninguna acción) — Fase 5 de la ruta.
- Recordatorios/notificaciones de revisión programada (hoy el semáforo es
  visual en la pantalla; no envía correos) — Fase 3 de la ruta.
- Migrar el binario de disco local a Object Storage S3-compatible con
  política WORM (ver "Almacenamiento del binario" arriba) — Fase S2.
- Aprobación multinivel (gerente de área + seguridad de la información) —
  Fase 2 de la ruta. Hoy aprueba cualquier Admin del tenant (un solo paso).
