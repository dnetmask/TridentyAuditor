# Indicador de cumplimiento del SGSI

**Estado:** ✅ Implementado (`backend/app/compliance`, `frontend/src/components/ComplianceMeter.tsx`)

Un solo porcentaje, visible en la barra superior en cualquier pantalla del
tenant, que avanza únicamente cuando se agrega evidencia real — no cuando se
marca una casilla. Nace de la pregunta que quedó abierta al construir
MOD·SOA/MOD·RSK: un cliente puede recorrer el asistente y llenar el SoA, pero
¿cómo sabe de un vistazo qué tan lejos está de una auditoría externa?

## Qué mide (y qué no)

El porcentaje combina dos señales que ya exigen un documento con una versión
**aprobada** (`app/documents/service.py::has_approved_version`) — no basta con
adjuntar un archivo en borrador:

| Componente | Peso | Numerador | Denominador |
|---|---|---|---|
| MOD·SOA | 60% | Controles aplicables con evidencia aprobada vinculada | Controles aplicables (`is_applicable=true`) |
| MOD·WZD | 40% | Tareas que exigen evidencia y están cerradas | Tareas que exigen evidencia (`requires_evidence=true`) |

Para MOD·WZD no hace falta re-verificar la evidencia en cada cálculo:
`complete_task` (sección [mod-wzd.md](mod-wzd.md)) ya impide cerrar una tarea
sin evidencia aprobada, así que "cerrada" implica "evidenciada" por
construcción. Para MOD·SOA no hay ese candado — marcar un control como
`implemented` no exige evidencia — así que ahí sí se verifica
`evidence_document_id` contra los documentos con versión aprobada en cada
cálculo.

Si un módulo no se ha iniciado (SoA sin instanciar, ciclo del asistente sin
arrancar), su componente cuenta como 0%, no se excluye del promedio — el
indicador empieza en 0% y solo sube con trabajo real, nunca aparece alto por
default.

**No incluye** (por ahora):

- MOD·RSK — la evidencia de tratamiento de riesgos responde "¿se aplicó el
  tratamiento?", una pregunta distinta de "¿el control está cumplido?".
- MOD·AUD — cerrar un hallazgo también exige evidencia aprobada (mismo
  candado, ver [mod-aud.md](mod-aud.md)), pero es una señal de "¿se corrigió
  lo que encontró el auditor?", no de "¿el control está cumplido?" — igual
  naturaleza que MOD·RSK, por eso queda fuera del promedio por ahora.
- NIST CSF 2.0 — Fase 2, sin cargar todavía.

## Cómo se actualiza en la UI

El estado vive en `ComplianceContext` (envuelve toda la app en `App.tsx`,
por fuera del `Layout` para sobrevivir a la navegación entre pantallas) y se
consulta una vez al montar la sesión. Las pantallas que pueden mover la
aguja llaman a `refresh()` después de una mutación exitosa:

- `SoaPage.tsx`: al vincular evidencia o cambiar aplicabilidad/estado.
- `WizardPage.tsx`: al instanciar, completar o reabrir una tarea.
- `DocumentsPage.tsx`: al aprobar una versión — aprobar retroactivamente
  puede validar evidencia que ya estaba vinculada en SoA o el asistente.

`ComplianceMeter.tsx` no hace polling; si el cálculo cambia por una acción
que esta plataforma no dispara desde el frontend (poco probable hoy), el
número se pone al día en la próxima navegación que dispare `refresh()`.

## Endpoint

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/compliance/overview` | `{ percentage, components: [{ key, label, evidenced, total, percentage }] }` — cualquier rol del tenant (incluido `viewer`) puede consultarlo |

## Pendiente

- Los pesos (60/40) y qué cuenta como "evidenciado" están fijos en código
  (`app/compliance/service.py`), no son configurables por tenant.
- Sin serie histórica — el número es el estado actual, no hay gráfico de
  tendencia todavía.
- Cuando se integren MOD·RSK, MOD·AUD y NIST CSF 2.0 habrá que decidir si
  entran al mismo promedio o quedan como indicadores aparte.
