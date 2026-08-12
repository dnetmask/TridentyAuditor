# Autenticación y roles

**Estado:** ✅ Implementado (`backend/app/auth`)

Login real con email/contraseña y cuatro roles, aplicando la separación
Netmask/cliente de la sección 07 del documento de arquitectura. Reemplaza el
mecanismo anterior (mintar un JWT de desarrollo sin credenciales) por
cuentas de verdad con contraseña con hash (bcrypt).

## Modelo

`User` vive en el plano de control (como `Tenant`), sin RLS — un Super Admin
no tiene `tenant_id`; los otros tres roles siempre pertenecen a un tenant.
Un JWT (HS256, placeholder hasta Keycloak/OIDC en la Fase 2) lleva
`sub`, `email`, `full_name`, `role` y, si aplica, `tenant_id`.

## Roles

| Rol | Alcance | Puede |
|---|---|---|
| **Super Admin** | Cross-tenant, sin `tenant_id` | Crear/listar tenants, crear usuarios para cualquier tenant. **No puede** llamar ningún endpoint de datos de un tenant (MOD·DOC, MOD·WZD) — su JWT no trae `tenant_id`, así que `decode_tenant_token` lo rechaza con 401. |
| **Admin del tenant** (`tenant_admin`) | Su tenant | Todo dentro del tenant: crear/editar/aprobar/rechazar documentos, instanciar y operar el ciclo SGSI, gestionar usuarios de su propio tenant (crear, cambiar rol, activar/desactivar) — pero no puede crear ni editar cuentas Super Admin. |
| **Auditor interno** (`internal_auditor`) | Su tenant | Crear/editar documentos y tareas del wizard (necesita subir su propia evidencia de auditoría), pero **no puede aprobar ni rechazar** versiones — esa es una decisión de autoridad reservada al Admin del tenant (segregación de funciones). No gestiona usuarios. |
| **Visualizador** (`viewer`) | Su tenant | Solo lectura: documentos, wizard, marco normativo. Ningún endpoint de escritura lo acepta. |

## Dónde se aplica

- `require_super_admin` — `POST/GET /api/v1/tenants`.
- `require_admin_principal` (Super Admin o Admin del tenant) — `POST/GET/PATCH /api/v1/auth/users`, con el tenant_id forzado al propio cuando quien llama es Admin del tenant (ver `app/auth/service.py::_assert_can_manage`).
- `require_tenant_roles(...)` — gatea cada endpoint de MOD·DOC y MOD·WZD; por ejemplo, aprobar/rechazar solo acepta `tenant_admin`.

`created_by` y `approved_by` en MOD·DOC (y, en general, quién hizo qué) ya no
son campos de texto libre que el cliente pueda inventar — se derivan del
`email` del JWT en el propio backend.

## Primer acceso

No hay huevo-o-gallina: crear la primera cuenta Super Admin requiere acceso
directo a la base de datos, porque el endpoint que crea usuarios ya exige
estar autenticado como Super Admin o Admin del tenant.

```bash
python scripts/create_super_admin.py admin@netmask.co --name "Nombre Apellido"
```

A partir de ahí, todo pasa por la API: el Super Admin crea tenants y el
primer Admin de cada uno; cada Admin del tenant crea a sus propios Auditores
internos y Visualizadores.

## Pendiente

- Sigue siendo HS256 con secreto compartido — la Fase 2 lo reemplaza por
  OIDC contra Keycloak (login federado, MFA, tokens asimétricos).
- Sin flujo de "olvidé mi contraseña" ni invitación por email — el Admin
  que crea la cuenta comparte la contraseña temporal por fuera de la
  plataforma.
- El acceso de soporte de Netmask a un tenant específico (bajo autorización
  y auditado, sección 07) no está modelado todavía — hoy Super Admin
  simplemente no tiene acceso, sin mecanismo de excepción.
