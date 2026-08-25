# Motor de frameworks

**Estado:** ✅ Implementado (`backend/app/frameworks`)

Implementación de la sección 03 del documento de arquitectura: `Framework →
Domain → Control → Requirement` como tablas de datos, no un esquema por
estándar. Es referencia global (no lleva `tenant_id`, no pasa por RLS) —
cargar una norma nueva es insertar filas, no migrar esquema.

## Una norma por tenant

Desde la Fase 0, cada `Tenant` trae un `framework_id` obligatorio (FK a
`frameworks.id`, elegido una sola vez al crearse desde el panel de Super
Admin — ver `docs/modules/auth-roles.md`). No es una FK "cruzada" como las de
MOD·DOC hacia `tenants`: `frameworks` vive en el mismo plano de control sin
RLS que `tenants`, así que no hay frontera de aislamiento que cruzar.

**Un tenant, una norma.** Si una organización necesita cumplir dos normas a
la vez (por ejemplo ISO/IEC 27001:2022 *y* la Guía de Ciberseguridad del
CNO), se crean dos tenants — sus estructuras de dominios y controles no son
compatibles entre sí ni tiene sentido mezclarlas en un solo SoA. El
`framework_code` del tenant viaja embebido en la respuesta de
`POST /api/v1/auth/login` (igual que `tenant_name`) para que el frontend
nunca tenga que adivinarlo ni dejarlo escrito a mano — MOD·SOA, Marco
normativo, MOD·RSK y MOD·AUD lo resuelven desde la sesión.

## Seeds incluidos

- **`app/frameworks/seeds/iso27001_2022.py`** — ISO/IEC 27001:2022: 4
  dominios (temas) y 93 controles del Anexo A, con su código y título
  oficial únicamente. El texto normativo completo de cada control/requisito
  es contenido licenciado del estándar y no se reproduce aquí; la tabla
  `requirements` queda vacía a propósito.
- **`app/frameworks/seeds/cno1960.py`** — Guía de Ciberseguridad del Consejo
  Nacional de Operación (Acuerdo 1960, sector eléctrico colombiano,
  basada en NERC-CIP): 10 numerales normativos y 41 controles, tomados del
  Anexo 3 (Lista de cumplimiento periódico) del Acuerdo. A diferencia de
  ISO 27001, este es texto regulatorio público colombiano — sin contenido
  licenciado de por medio — así que el seed sí carga `requirements` con cada
  ítem de evidencia del Anexo 3 (varios controles traen 2 o más).

Ambos seeds corren en cada arranque de la API (`lifespan` en `app/main.py`)
y son idempotentes — insertan lo que falte y actualizan lo ya existente, así
que ampliar un seed se refleja en despliegues ya sembrados sin migración.

Cada control trae `evidence_guidance`: una guía práctica de qué
documento/artefacto suele demostrarlo. En ISO 27001 la redacta el equipo de
Netmask; en CNO-1960 se deriva directamente de la columna "Actividad /
Soporte / Evidencia" del Anexo 3. Se muestra en Marco normativo y en MOD·SOA
junto a cada control, como punto de partida para armar la carpeta de
evidencia — no reemplaza el criterio del auditor. Dos columnas del Anexo 3
quedan deliberadamente fuera de `evidence_guidance`: la "Propuesta prórroga"
(plazos de transición del Acuerdo 1960 sobre el Acuerdo 1502 anterior,
información de 2025-2028, no una guía permanente) y, a diferencia de esa,
"Aplicabilidad plantas menores" sí se conserva como una frase al final de la
guía cuando aplica.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/frameworks` | Lista frameworks cargados — alimenta el selector de norma al crear un tenant |
| GET | `/api/v1/frameworks/{code}` | Framework con dominios y controles anidados |
| GET | `/api/v1/frameworks/{code}/domains` | Dominios de un framework |
| GET | `/api/v1/domains/{domain_id}/controls` | Controles de un dominio |
| GET | `/api/v1/controls/{control_id}` | Detalle de un control con sus requisitos |

Sin autenticación — son datos de referencia, iguales para todos los tenants
que comparten la misma norma.

## Cargar NIST CSF 2.0 (Fase 2)

Agregar un `Framework(code="NIST_CSF_2.0", ...)` con sus `Domain`/`Control`
correspondientes (Gobernar, Identificar, Proteger, Detectar, Responder,
Recuperar) siguiendo el mismo patrón de `iso27001_2022.py` o `cno1960.py` —
no requiere migración de esquema. Sí aparecerá automáticamente como una
tercera opción en el selector de norma del panel de Super Admin en cuanto
`GET /api/v1/frameworks` lo liste.

## Pendiente

- El Asistente paso a paso (MOD·WZD, "Ruta SGSI") sigue escrito para la
  metodología de implementación de un SGSI ISO 27001 (diagnóstico → contexto
  → liderazgo → riesgos → SoA → implementación → auditoría interna →
  revisión y certificación) — no encaja con el modelo de cumplimiento
  regulatorio de plazos fijos de CNO-1960. Sigue visible tal cual para un
  tenant CNO-1960 aunque su texto no le calce; diseñarle una ruta propia es
  trabajo aparte.
