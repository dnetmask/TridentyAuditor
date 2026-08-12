# Motor de frameworks

**Estado:** ✅ Implementado (`backend/app/frameworks`)

Implementación de la sección 03 del documento de arquitectura: `Framework →
Domain → Control → Requirement` como tablas de datos, no un esquema por
estándar. Es referencia global (no lleva `tenant_id`, no pasa por RLS) — la
aplicabilidad por tenant es responsabilidad de MOD·SOA (pendiente).

## Seed incluido

`app/frameworks/seeds/iso27001_2022.py` carga ISO/IEC 27001:2022: 4 dominios
(temas) y 93 controles del Anexo A, con su código y título oficial
únicamente. El texto normativo completo de cada control/requisito es
contenido licenciado del estándar y no se reproduce aquí; la tabla
`requirements` queda disponible para cuando se cargue ese texto o para NIST
CSF 2.0 en la Fase 2. El seed corre en cada arranque de la API (`lifespan` en
`app/main.py`) y es idempotente — también actualiza (no solo inserta) para
que ampliar el seed se refleje en despliegues ya sembrados.

Cada control también trae `evidence_guidance`: una guía práctica redactada
por el equipo (no texto del estándar) de qué documento/artefacto suele
demostrarlo — ej. para A.5.1 "Política de seguridad... aprobada por la
dirección y evidencia de su publicación". Se muestra en Marco normativo y en
MOD·SOA junto a cada control, como punto de partida para armar la carpeta de
evidencia — no reemplaza el criterio del auditor.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/frameworks` | Lista frameworks cargados |
| GET | `/api/v1/frameworks/{code}` | Framework con dominios y controles anidados |
| GET | `/api/v1/frameworks/{code}/domains` | Dominios de un framework |
| GET | `/api/v1/domains/{domain_id}/controls` | Controles de un dominio |
| GET | `/api/v1/controls/{control_id}` | Detalle de un control con sus requisitos |

Sin autenticación — son datos de referencia, iguales para todos los tenants.

## Cargar NIST CSF 2.0 (Fase 2)

Agregar un `Framework(code="NIST_CSF_2.0", ...)` con sus `Domain`/`Control`
correspondientes (Gobernar, Identificar, Proteger, Detectar, Responder,
Recuperar) siguiendo el mismo patrón de `iso27001_2022.py` — no requiere
migración de esquema.
