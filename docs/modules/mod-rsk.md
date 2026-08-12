# MOD·RSK — Gestión de riesgos

**Fase:** 1 · **Estado:** ✅ Implementado (`backend/app/risk`, `frontend/src/pages/RiskPage.tsx`)

Inventario de activos, matriz de riesgo (probabilidad × impacto), plan de
tratamiento y seguimiento de riesgo residual. Se apoya en el motor de
frameworks para vincular cada riesgo con los controles que lo tratan (ver
[frameworks-engine.md](frameworks-engine.md)) y en MOD·DOC para adjuntar
evidencia del tratamiento.

## Modelo

- **Asset**: inventario de activos del tenant (`AssetCategory`:
  información/software/hardware/servicio/personas/instalación/otro), con
  dueño opcional.
- **Risk**: `likelihood` e `impact` (1-5 cada uno) calculan `inherent_score`
  (producto) e `inherent_level` al crear o al editar cualquiera de los dos.
  El tratamiento (`treatment_decision`: mitigar/aceptar/transferir/evitar,
  más `treatment_plan` en texto libre) y el riesgo residual
  (`residual_likelihood`/`residual_impact` → `residual_score`/
  `residual_level`) se registran por separado — el riesgo inherente nunca
  se sobreescribe con el residual. `status` sigue abierto → en tratamiento →
  cerrado. `evidence_document_id` enlaza a MOD·DOC.
- **RiskControlLink**: M2M entre `Risk` y `Control` (con `tenant_id`
  denormalizado para que la política RLS no tenga que hacer join) —
  responde "¿qué controles mitigan este riesgo?" y, mirado al revés, sirve
  para trazar cobertura control→riesgo en una futura vista de auditoría.

## Reglas de negocio

- **Bandas de nivel de riesgo** (fijas en esta fase, no configurables por
  tenant): score ≤ 4 → bajo, ≤ 9 → medio, ≤ 15 → alto, > 15 → crítico. Se
  aplican igual al inherente y al residual.
- Editar `likelihood`/`impact` en un `PATCH` recalcula `inherent_score` y
  `inherent_level` en el servidor; editar los campos `residual_*` recalcula
  `residual_score`/`residual_level` de forma independiente. El cliente
  nunca envía el score/nivel calculado, solo los insumos.
- Vincular/desvincular controles reemplaza el conjunto completo
  (`control_ids: [...]` en el `PATCH` borra y recrea los enlaces) — no hay
  endpoint incremental de agregar-uno-quitar-uno.
- La metodología de valoración (probabilidad × impacto 1-5) es fija por
  diseño en esta fase; "metodología configurable" del documento de
  arquitectura queda como mejora futura.

## Endpoints

Todos requieren `Authorization: Bearer <jwt>` de un tenant.

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/risk/assets` | Crea un activo (`tenant_admin`, `internal_auditor`) |
| GET | `/api/v1/risk/assets` | Lista los activos del tenant |
| PATCH | `/api/v1/risk/assets/{id}` | Edita un activo |
| POST | `/api/v1/risk/risks` | Crea un riesgo (calcula el nivel inherente) |
| GET | `/api/v1/risk/risks` | Lista los riesgos con sus controles vinculados |
| PATCH | `/api/v1/risk/risks/{id}` | Actualiza tratamiento, residual, dueño, estado o controles |

## Pendiente

- Sin matriz visual 5×5 (heatmap) — hoy el nivel se muestra como badge de
  texto en la tabla, no como una cuadrícula probabilidad/impacto.
- Sin historial de cambios de nivel (sabemos el estado actual, no la
  trayectoria de cómo llegó ahí).
- Sin vista de "cobertura" que cruce riesgos por control/dominio para
  priorización — el enlace M2M existe pero no hay un reporte agregado
  todavía.
