# MOD·DOC — Control documental

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/documents`)

Versionado y flujo de aprobación de documentos, con RLS por tenant. Base
sobre la que colgará la evidencia de los demás módulos (MOD·RSK, MOD·SOA,
MOD·AUD, ...).

## Modelo

- **Document**: identidad estable de un documento (código, título, tipo,
  vínculo opcional a un `Control` del motor de frameworks, retención).
- **DocumentVersion**: cada versión de ese documento, con su propio ciclo de
  vida, más el binario subido (`original_filename`, `content_type`,
  `file_size`) y una referencia interna `storage_ref` al archivo en disco.

## Almacenamiento del binario

Cada versión exige adjuntar un archivo real — ya no existe un campo de texto
libre tipo `storage_ref` manual. El binario se guarda en disco local bajo
`Settings.documents_storage_dir` (`TRIDENTY_DOCUMENTS_STORAGE_DIR`), en la
ruta `{tenant_id}/{document_id}/{version_id}` (sin extensión — el nombre
original solo se conserva como metadato para la descarga, así que no hay
superficie de path traversal que sanear). En `deploy/docker-compose.yml`
vive en el volumen `tridenty_documents`, igual que Postgres vive en
`tridenty_pgdata` — sobrevive a `docker compose down` pero no a un `-v`.

Es almacenamiento local, coherente con el tier on-prem/air-gapped de la
sección 04 (funciona sin ningún servicio externo). Migrar a Object Storage
S3-compatible con política WORM — para HA multi-réplica y retención
inmutable de verdad — sigue pendiente como hardening de producción.

## Flujo de aprobación (copias controladas)

```
   draft ──submit──▶ in_review ──approve──▶ approved
     ▲                    │                     │
     └──────reject────────┘         (aprobar otra versión
                                      marca esta como)
                                             ▼
                                         obsolete
```

- Solo puede haber una versión en `draft`/`in_review` a la vez por documento
  — hay que resolverla antes de abrir otra.
- Al aprobar una versión, cualquier versión previamente `approved` del mismo
  documento pasa a `obsolete` automáticamente (una sola copia vigente).
- No existe endpoint para editar o borrar una versión `approved` — es
  intencional: sección 06 del documento de arquitectura exige evidencia
  inmutable una vez publicada.

## Endpoints

Todos requieren `Authorization: Bearer <jwt>` con claims `tenant_id`, `sub`,
`role` (ver `backend/scripts/make_dev_token.py` para generar uno de prueba).

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/documents` | `multipart/form-data` — crea un documento + versión 1 en `draft` con el archivo adjunto |
| GET | `/api/v1/documents` | Lista documentos del tenant |
| GET | `/api/v1/documents/{id}` | Detalle con todas sus versiones |
| POST | `/api/v1/documents/{id}/versions` | `multipart/form-data` — abre una nueva versión en `draft` con su propio archivo |
| GET | `/api/v1/documents/{id}/versions/{n}/file` | Descarga el binario de esa versión (`Content-Disposition: attachment`) |
| POST | `/api/v1/documents/{id}/versions/{n}/submit` | `draft` → `in_review` |
| POST | `/api/v1/documents/{id}/versions/{n}/reject` | `in_review` → `draft` |
| POST | `/api/v1/documents/{id}/versions/{n}/approve` | `in_review` → `approved` |

Los dos POST que crean documento/versión reciben `multipart/form-data` (campos
de texto vía `Form` + el archivo vía `File`), no JSON — es la única forma de
adjuntar un binario en el mismo request. Límite de tamaño configurable con
`TRIDENTY_DOCUMENTS_MAX_FILE_SIZE_MB` (25 MB por defecto).

## Pendiente

- Listas maestras y política de retención automatizada (hoy `retention_months`
  se guarda pero no dispara ninguna acción).
- Migrar el binario de disco local a Object Storage S3-compatible con
  política WORM (ver "Almacenamiento del binario" arriba).
- Reglas de quién puede aprobar (hoy cualquier `role` autenticado puede;
  falta el chequeo de rol Admin del tenant / Dueño de control de la sección 07).
