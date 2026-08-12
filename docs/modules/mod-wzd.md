# MOD·WZD — Asistente paso a paso

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/wizard`, `frontend/src/pages/WizardPage.tsx`)

Convierte la metodología de 8 fases (diagnóstico → contexto → liderazgo →
riesgos → SoA → implementación → auditoría interna → revisión y
certificación) en tareas asignadas, con dueño, fecha y evidencia requerida
por fase — ver sección 02 del documento de arquitectura.

## Modelo

- **WizardPhase** / **WizardTaskTemplate**: checklist de referencia global
  (igual patrón que el motor de frameworks — dato, no esquema). El seed
  (`app/wizard/seeds/methodology.py`) carga las 8 fases con 3-4 tareas cada
  una, basadas en práctica estándar de implementación ISO 27001.
- **TenantWizardTask**: la instancia editable de cada tenant, con RLS. Se
  crea vía `POST /api/v1/wizard/instantiate` (idempotente — solo agrega lo
  que falte si el checklist global crece). Un tenant también puede agregar
  tareas propias fuera del checklist (`template_id` nulo).

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

Todos (salvo `/phases`) requieren `Authorization: Bearer <jwt>`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/wizard/phases` | Checklist de referencia (global, sin auth) |
| POST | `/api/v1/wizard/instantiate` | Crea las tareas del tenant a partir del checklist |
| GET | `/api/v1/wizard/progress` | Las 8 fases con sus tareas y estado (`locked`/`current`/`complete`) |
| POST | `/api/v1/wizard/tasks` | Agrega una tarea custom a una fase |
| PATCH | `/api/v1/wizard/tasks/{id}` | Asigna dueño, fecha o evidencia (solo si no está `done`) |
| POST | `/api/v1/wizard/tasks/{id}/complete` | Cierra la tarea (valida evidencia + fase desbloqueada) |
| POST | `/api/v1/wizard/tasks/{id}/reopen` | Regresa la tarea a `pending` |

## Pendiente

- El ciclo de mejora continua (cerrar la fase 8 y volver a abrir la fase 1
  como una nueva vuelta) no está implementado — hoy el recorrido es lineal.
- Sin recordatorios/notificaciones por fecha de vencimiento (depende de
  RabbitMQ/NATS, sección 05 — todavía no integrado).
- La fase 8 (Revisión y certificación) no tiene módulo propio de
  certificación; sus tareas son genéricas.
