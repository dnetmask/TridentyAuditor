# Bitácora de auditoría (activity log)

**Fase:** S1 · **Estado:** ✅ Implementado (`backend/app/activity`)

El "audit trail" de la plataforma — sección 06 del documento de
arquitectura: *la herramienta de auditoría también se audita*. Distinto de
MOD·AUD (que son las auditorías internas de negocio del tenant): esto
registra qué hizo cada cuenta dentro de TridentyAuditor.

## Qué registra

| Acción | Cuándo |
|---|---|
| `auth.login` / `auth.login_failed` / `auth.login_locked` | cada intento de sesión (los fallos persisten aunque el request termine en 401) |
| `auth.logout` | revocación del refresh token |
| `tenants.created` | alta de un tenant (con su norma) |
| `users.created` / `users.updated` | gestión de cuentas, con los campos tocados |
| `documents.created` / `version_created` / `submitted` / `approved` / `rejected` / `downloaded` | ciclo de vida documental completo, descargas incluidas |
| `soa.instantiated` / `wizard.instantiated` | arranque del SoA y de la ruta paso a paso |

Cada evento: actor (email + id), tenant, entidad, detalle corto, IP
(respetando `X-Forwarded-For`) y timestamp. **Append-only**: ningún service
tiene UPDATE ni DELETE sobre la tabla.

## Diseño

- `activity_events` vive sin RLS, como `users`: guarda también eventos del
  plano de control (login de Super Admin, alta de tenants) que no tienen
  tenant. El endpoint de consulta filtra por el tenant del token.
- Dos vías de escritura (`app/activity/service.py`): `log_event` viaja en la
  transacción del request (si la acción falla y hace rollback, el evento
  desaparece con ella — solo se auditan acciones que ocurrieron);
  `log_event_now` confirma en su propia transacción, para registrar
  *fracasos* como logins fallidos que acompañan a un 401.

## Endpoint

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/activity?limit=` | Últimos eventos del propio tenant, más reciente primero (solo `tenant_admin`) |

## Pendiente

- Sin pantalla en el frontend — hoy se consulta por API o directo en BD.
- Sin exportación ni retención configurable de la bitácora.
- Los eventos del plano de control (Super Admin) no tienen endpoint de
  consulta propio todavía.
