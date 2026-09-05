# MOD·DOC — Control documental

**Fases:** 1, 2 y 3 · **Estado:** ✅ Implementado (`backend/app/documents`, `backend/app/areas`)

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

## Flujo de aprobación multinivel (copias controladas)

```
   draft ──submit──▶ in_review ──firma 1──▶ in_review ──firma 2──▶ approved
     ▲                    │        (gerente de área,      (seguridad de la
     └──────reject────────┘         si hay área)           información)
        (motivo obligatorio;                                    │
         borra firmas parciales)              (aprobar otra versión
                                               marca esta como)
                                                      ▼
                                                  obsolete
```

**Dos firmas por versión (Fase 2).** `POST .../approve` firma el siguiente
paso pendiente, no aprueba de golpe:

1. **Gerente de área** — solo si el documento tiene área asignada. Firma el
   `manager_user_id` del área, o cualquier Admin del tenant en su lugar
   (área sin gerente no bloquea el flujo). El gerente puede tener cualquier
   rol: la autorización la decide el servicio, no el rol del endpoint.
2. **Seguridad de la información** — siempre obligatoria, siempre la última,
   y solo la firma un Admin del tenant. Es la que publica la versión.

Cada firma queda en `document_approvals` con su **sello verificable**:
`(paso, firmante, timestamp, SHA-256 del binario al momento de firmar)` — la
firma queda amarrada al archivo exacto que se aprobó, no a un registro
mutable. El mismo Admin puede firmar ambos pasos (bloquearlo dejaría muerto
el flujo en tenants de una sola persona); ambas firmas quedan registradas
por separado de todas formas.

- Solo puede haber una versión en `draft`/`in_review` a la vez por documento
  — hay que resolverla antes de abrir otra.
- Al quedar aprobada una versión, cualquier versión previamente `approved`
  del mismo documento pasa a `obsolete` automáticamente (una sola copia
  vigente), y se recalcula `next_review_date` si hay frecuencia de revisión.
- Rechazar exige un motivo, que queda en la versión (`rejection_reason`) y
  en la bitácora — y **elimina las firmas parciales**: el siguiente envío a
  revisión arranca la aprobación desde cero (la bitácora conserva el rastro
  de quién había firmado).
- Las versiones aprobadas antes de la Fase 2 conservan su
  `approved_by`/`approved_at` de un solo paso — no se les inventan firmas
  retroactivas.
- No existe endpoint para editar o borrar una versión `approved` — es
  intencional: sección 06 del documento de arquitectura exige evidencia
  inmutable una vez publicada.

## Copias controladas al servir (Fase 3)

Toda copia que sale de la plataforma es, por definición, **no controlada** —
la controlada es la que vive aquí. Por eso los **PDF se estampan en el
momento de servirlos** (`app/documents/stamping.py`, pypdf + reportlab):

- **Pie en todas las páginas**: `Copia no controlada · CÓDIGO vN ·
  descargada el FECHA por USUARIO` — trazabilidad de la copia impresa.
- **Marca de agua diagonal** cuando lo servido NO es la copia vigente:
  `BORRADOR`, `EN REVISIÓN`, `OBSOLETO`, o `DEROGADO` si el documento
  entero fue retirado — ISO 7.5.3.d exige prevenir el uso de información
  obsoleta, y sin esto un PDF obsoleto descargado ayer es indistinguible
  del vigente.

La verificación SHA-256 corre sobre el binario original ANTES de estampar
(el sello nunca enmascara un archivo adulterado, y el hash registrado sigue
correspondiendo al original almacenado). El sello es defensa documental, no
frontera de seguridad: un PDF no procesable (corrupto, cifrado) se sirve
original en vez de romper la descarga, y los formatos no-PDF (Office,
imágenes, texto) salen tal cual.

**Botón Ver**: `?inline=true` en el endpoint de archivo lo entrega con
`Content-Disposition: inline` — el frontend lo abre en una pestaña nueva
para leerlo sin descargarlo (PDF, imágenes y texto; Office siempre se
descarga). Ambas vías quedan en la bitácora (`documents.downloaded`, con
"vista inline" cuando aplica).

**Panel Elaboró / Revisó / Aprobó**: cada versión aprobada u obsoleta
muestra los tres nombres — elaboró (`created_by`), revisó (firma del
gerente de área) y aprobó (firma de seguridad de la información; en
versiones anteriores a la Fase 2, el `approved_by` de un solo paso).

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
| GET | `/api/v1/documents/{id}/versions/{n}/file` | Sirve el binario (verifica SHA-256; PDF sale estampado). `?inline=true` para leer en el navegador (botón Ver) |
| POST | `/api/v1/documents/{id}/versions/{n}/submit` | `draft` → `in_review` |
| POST | `/api/v1/documents/{id}/versions/{n}/reject` | `in_review` → `draft`, con `reason` obligatorio; borra firmas parciales |
| POST | `/api/v1/documents/{id}/versions/{n}/approve` | Firma el siguiente paso pendiente (gerente de área → seguridad); con la última firma pasa a `approved` y recalcula próxima revisión |
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
≤30 días en ámbar, verde "faltan N días" cuando hay margen), badge
"Derogado", panel de detalle con chips de controles, hash SHA-256 y el
**checklist de firmas** de cada versión (paso, firmante, fecha), botón de
firma según quién es el usuario (gerente del área o Admin), edición de
metadatos, derogación con motivo, sugerencia automática de código al elegir
tipo, y gestión de áreas (crear/listar con gerente) desde la misma pantalla.

## Pendiente

- Listas maestras y política de retención automatizada (hoy `retention_months`
  se guarda pero no dispara ninguna acción) — Fase 5 de la ruta.
- Recordatorios/notificaciones de revisión programada (hoy el semáforo es
  visual en la pantalla; no envía correos) — Fase 3 de la ruta.
- Migrar el binario de disco local a Object Storage S3-compatible con
  política WORM (ver "Almacenamiento del binario" arriba) — Fase S2.
- El sello aplica solo a PDF; estampar Office exigiría convertir a PDF al
  servir (LibreOffice headless) — candidato a Fase 5 si se necesita.
