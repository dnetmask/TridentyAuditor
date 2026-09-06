# MOD·PRC — Mapa de procesos + Panel de entrada

**Fase:** 4 · **Estado:** ✅ Implementado (`backend/app/processes`, `backend/app/dashboard`)

Da respuesta a dos observaciones del usuario y a la comparación con Kawak: un
**mapa de procesos** donde cuelgan los documentos, y un **dashboard de
entrada** que muestra el estado del SGSI de un vistazo. Ambos reutilizan
entidades y patrones ya existentes — no introducen un motor nuevo.

## Mapa de procesos

**Process** — por tenant, con RLS; nombre único por tenant. Jerarquía simple
(`parent_id`: un proceso puede tener padre y subprocesos), responsable
opcional (usuario del tenant) y orden. Los documentos cuelgan por
**DocumentProcessLink** (M2M, mismo patrón que `RiskControlLink`).

- `GET /api/v1/processes/tree` devuelve el árbol: cada nodo trae sus
  documentos, sus subprocesos anidados y un `document_count` **acumulado**
  (documentos propios + de los subprocesos), para ver el peso de un proceso
  raíz de un vistazo.
- CRUD en `/api/v1/processes` — escribe el Admin del tenant, lee cualquier
  rol. La validación de jerarquía evita que un proceso sea su propio padre o
  forme un ciclo. Borrar un proceso deja a sus hijos como raíces
  (`parent_id → NULL`) y quita sus enlaces de documentos (los documentos en
  sí no se tocan).
- `document_ids` en create/update reemplaza el conjunto completo de enlaces
  (semántica de MOD·RSK).

En la pantalla `/procesos`, el árbol es expandible; al hacer clic en un
documento se abre en el **visor embebido** sin salir de la página.

## Visor embebido de documentos

Componente `DocumentViewer` (`frontend/src/components/DocumentViewer.tsx`):
trae el binario **estampado** (mismo endpoint `?inline=true` de la Fase 3)
como blob y lo muestra en un `<iframe>` dentro de un modal — PDF, imágenes y
texto, sin descargar. Se usa desde el mapa de procesos y desde el botón
**Ver** de la pantalla de Documentos (que antes abría una pestaña nueva).

## Panel de entrada (dashboard)

`GET /api/v1/dashboard/overview` (`backend/app/dashboard`) reúne en una sola
llamada, para el tenant del token:

- **Cumplimiento**: el mismo `compliance/overview` (SoA + asistente + legal).
- **Documentos**: vigentes, revisiones vencidas, próximas (≤30 días) y
  versiones en revisión (pendientes de aprobar).
- **Riesgos**: por estado (abiertos / en tratamiento / cerrados).
- **Auditoría**: programas y hallazgos abiertos/cerrados.
- **Requisitos legales**: por calificación (cumple / parcial / no cumple).
- **SoA**: total y aplicables. **Procesos**: total.
- **Higiene documental** (`documental_hygiene`): vencidos, por vencer, sin
  revisión programada, % al día sobre los programados y promedio de días de
  implementación (del alta del documento a la aprobación de su versión
  vigente) — la lectura de "¿está al día?" que Kawak resuelve con un gauge de
  "% vencidos". Complementa, no reemplaza, el indicador de cumplimiento: mide
  vigencia/frescura, no madurez de implementación del SGSI.

Es orquestación de solo lectura — no agrega lógica de negocio nueva. La
pantalla `/panel` es la nueva página de llegada de los roles de tenant
(antes era la Ruta SGSI): un medidor de cumplimiento global con sus
componentes y una grilla de tarjetas que enlazan a cada módulo, con semáforo
en revisiones vencidas y riesgos/hallazgos abiertos, más un **panel de
higiene documental** al pie.

## Pendiente

- El "mapa" es hoy un árbol expandible; un editor visual de diagramas
  (cajas y flechas arrastrables) es un proyecto aparte, no un prerrequisito
  — candidato a fase futura si el cliente lo valora.
- Serie histórica del cumplimiento (tendencia en el tiempo) — hoy el panel
  es una foto del estado actual.
- Enlazar procesos también a controles/riesgos (hoy solo a documentos), si
  se necesita para el análisis de cobertura por proceso.
