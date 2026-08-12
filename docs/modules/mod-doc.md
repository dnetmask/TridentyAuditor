# MOD·DOC — Control documental

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/documents`)

Versionado y flujo de aprobación de documentos, con RLS por tenant. Base
sobre la que colgará la evidencia de los demás módulos (MOD·RSK, MOD·SOA,
MOD·AUD, ...).

## Modelo

- **Document**: identidad estable de un documento (código, título, tipo,
  vínculo opcional a un `Control` del motor de frameworks, retención).
- **DocumentVersion**: cada versión de ese documento, con su propio ciclo de
  vida. `storage_ref` es un placeholder para la referencia real en Object
  Storage S3-compatible (sección 05) — el binario en sí no se maneja en este
  esqueleto.

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
| POST | `/api/v1/documents` | Crea un documento + versión 1 en `draft` |
| GET | `/api/v1/documents` | Lista documentos del tenant |
| GET | `/api/v1/documents/{id}` | Detalle con todas sus versiones |
| POST | `/api/v1/documents/{id}/versions` | Abre una nueva versión en `draft` |
| POST | `/api/v1/documents/{id}/versions/{n}/submit` | `draft` → `in_review` |
| POST | `/api/v1/documents/{id}/versions/{n}/reject` | `in_review` → `draft` |
| POST | `/api/v1/documents/{id}/versions/{n}/approve` | `in_review` → `approved` |

## Pendiente

- Listas maestras y política de retención automatizada (hoy `retention_months`
  se guarda pero no dispara ninguna acción).
- Subida real a Object Storage S3-compatible con política WORM.
- Reglas de quién puede aprobar (hoy cualquier `role` autenticado puede;
  falta el chequeo de rol Admin del tenant / Dueño de control de la sección 07).
