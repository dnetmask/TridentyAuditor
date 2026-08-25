# MOD·WZD — Asistente paso a paso

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/wizard`, `frontend/src/pages/WizardPage.tsx`)

Convierte la ruta de puesta en marcha de la norma del tenant en tareas
asignadas, con dueño, fecha y evidencia requerida por fase. Cada norma trae
su propia ruta — no hay una sola metodología universal (ver "Una norma por
tenant" en [frameworks-engine.md](frameworks-engine.md)):

- **Ruta SGSI** (ISO/IEC 27001:2022, `app/wizard/seeds/methodology.py`): 8
  fases de un proyecto de implementación desde cero (diagnóstico → contexto
  → liderazgo → riesgos → SoA → implementación → auditoría interna →
  revisión y certificación) — ver sección 02 del documento de arquitectura.
- **Ruta CNO** (CNO-1960, `app/wizard/seeds/cno_route.py`): 10 fases, una
  por cada numeral del Anexo 1 del Acuerdo 1960 (mismo orden que sus
  dominios en Marco normativo/SoA). A diferencia de ISO, CNO-1960 no es un
  proyecto de implementación desde cero sino una obligación regulatoria ya
  vigente con controles de cumplimiento periódico — así que la Ruta CNO no
  repite los 41 controles uno a uno (eso ya vive en MOD·SOA con su propia
  guía de evidencia), sino que agrupa la primera puesta en marcha de cada
  numeral en 2-4 tareas de alto nivel, nombrando el entregable más relevante
  y remitiendo a MOD·SOA para el resto del detalle.

## Modelo

- **WizardPhase** / **WizardTaskTemplate**: checklist de referencia global
  (igual patrón que el motor de frameworks — dato, no esquema). Cada fase
  trae un `framework_id` obligatorio: pertenece a una sola ruta, con su
  propia numeración (la Ruta SGSI y la Ruta CNO ambas empiezan en la fase
  1) — unicidad compuesta `(framework_id, number)` y `(framework_id, code)`.
- **TenantWizardTask**: la instancia editable de cada tenant, con RLS. Se
  crea vía `POST /api/v1/wizard/instantiate` (idempotente — solo agrega lo
  que falte, y solo de la ruta de SU norma, nunca de la otra). Un tenant
  también puede agregar tareas propias fuera del checklist (`template_id`
  nulo).

## Reglas de negocio

- **Evidencia obligatoria bloquea el cierre.** Una tarea con
  `requires_evidence=true` no se puede marcar `done` sin un
  `evidence_document_id` que apunte a un documento de MOD·DOC con al menos
  una versión `approved`. Vincular un documento en borrador no alcanza.
- **Una fase no se desbloquea hasta que la anterior está completa.** La
  fase 1 siempre está disponible; la fase N requiere que el 100% de las
  tareas de la fase N-1 estén en `done` (evidencia o no). El backend lo
  valida en `complete_task`, no solo la UI.
- **Reabrir** (`POST .../reopen`) regresa una tarea a `pending` — eso puede
  volver a bloquear las fases siguientes si ya se habían desbloqueado.
- El orden de las tareas se guarda en una columna `order_index` explícita,
  no se infiere de `created_at`: todas las tareas de una instanciación caen
  en la misma transacción, y `now()` en Postgres devuelve el inicio de la
  transacción — ordenar por `created_at` habría sido no determinista.
- `description` en cada tarea (plantilla y ya instanciada) es una guía de
  qué evidencia suele demostrar que la tarea está resuelta (ej. "Informe de
  diagnóstico... con las brechas identificadas"), no una explicación de qué
  es la tarea. Se muestra bajo el título en la pantalla del asistente.

## Endpoints

Todos (salvo `/phases`) requieren `Authorization: Bearer <jwt>` de un
tenant, y operan sobre la ruta de SU norma — el backend la resuelve del
tenant en sesión, el cliente nunca la elige.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/wizard/phases` | Checklist de referencia (global, sin auth) — `?framework_code=` filtra a una sola ruta, sin el parámetro trae ambas |
| POST | `/api/v1/wizard/instantiate` | Crea las tareas del tenant a partir del checklist de su norma |
| GET | `/api/v1/wizard/progress` | Las fases de la ruta del tenant con sus tareas y estado (`locked`/`current`/`complete`) |
| POST | `/api/v1/wizard/tasks` | Agrega una tarea custom a una fase |
| PATCH | `/api/v1/wizard/tasks/{id}` | Asigna dueño, fecha o evidencia (solo si no está `done`) |
| POST | `/api/v1/wizard/tasks/{id}/complete` | Cierra la tarea (valida evidencia + fase desbloqueada) |
| POST | `/api/v1/wizard/tasks/{id}/reopen` | Regresa la tarea a `pending` |

## Pendiente

- El ciclo de mejora continua (cerrar la última fase y volver a abrir la
  fase 1 como una nueva vuelta) no está implementado — hoy el recorrido es
  lineal en ambas rutas.
- Sin recordatorios/notificaciones por fecha de vencimiento (depende de
  RabbitMQ/NATS, sección 05 — todavía no integrado).
- La fase 8 de la Ruta SGSI (Revisión y certificación) no tiene módulo
  propio de certificación; sus tareas son genéricas. La Ruta CNO no tiene
  un equivalente — CNO-1960 no se certifica, se reporta al CNO.
- Cargar NIST CSF 2.0 (Fase 2) también implicará diseñarle su propia ruta,
  siguiendo el mismo patrón (`framework_id` + seed propio) que
  `methodology.py`/`cno_route.py`.
