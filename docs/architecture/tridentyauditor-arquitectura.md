# TridentyAuditor — Documento de Arquitectura

> Netmask · Uso interno · V0.1 — Borrador de discusión · Agosto 2026
> Nombres de producto, fases y cifras de alcance son propuestas de trabajo, no compromisos contractuales.

Plataforma GRC multitenant, nativa de contenedores — gestión documental y
seguimiento paso a paso de un Sistema de Gestión de Seguridad de la
Información, pensada como Kawak pero como SaaS: un solo motor de frameworks
que hoy habla ISO/IEC 27001:2022 y mañana habla NIST CSF 2.0, empaquetado en
contenedores OCI para servir a muchos clientes de Netmask desde cualquier
nube o desde el centro de datos del propio cliente.

- **Nombre de trabajo:** TridentyAuditor
- **Fase 1:** ISO/IEC 27001:2022 · **Fase 2:** NIST CSF 2.0
- **Despliegue:** contenedores · cualquier nube / on-prem
- **Modelo:** SaaS multitenant

## 00 · Resumen ejecutivo — Un motor de cumplimiento, no un formulario de ISO

Herramientas de referencia como Kawak resuelven bien el seguimiento de un
SGSI para *un* cliente. TridentyAuditor parte de un supuesto distinto:
Netmask atiende a muchos clientes, con distintos frameworks, distintos
niveles de madurez y distintos requisitos de aislamiento de datos — así que
la plataforma debe ser multitenant desde el modelo de datos hacia arriba, y
agnóstica de framework desde el motor hacia abajo.

Cuatro decisiones atraviesan todo el documento:

1. Los controles, dominios y requisitos no están hardcodeados a ISO 27001 —
   viven en un motor de frameworks pensado para recibir NIST CSF 2.0 en la
   Fase 2 sin reescribir el núcleo.
2. El aislamiento de datos es una decisión por tenant, no una decisión de
   arquitectura fija — pymes comparten infraestructura con Row-Level
   Security, clientes regulados obtienen base de datos y secretos dedicados.
3. Todo el stack corre como contenedores OCI sobre Kubernetes — el mismo
   Helm chart despliega en Azure, en cualquier otra nube o en un clúster
   dentro del centro de datos de un cliente regulado, sin reescribir nada.
4. La plataforma que audita cumplimiento debe poder demostrar el suyo —
   evidencia inmutable, bitácoras de auditoría y una cadena de suministro de
   contenedores verificable.

## 01 · Arquitectura funcional — Ocho módulos sobre un mismo núcleo

Cada módulo es una vista distinta sobre las mismas entidades del motor de
frameworks (dominio, control, riesgo, evidencia, hallazgo). Ninguno es una
isla de datos aparte.

| Código | Módulo | Fase | Descripción |
|---|---|---|---|
| MOD·DOC | Control documental | 1 | Versionado, flujo de aprobación, copias controladas, listas maestras y retención — la base sobre la que cuelga la evidencia de todos los demás módulos. |
| MOD·RSK | Gestión de riesgos | 1 | Inventario de activos, metodología de valoración configurable, matriz de riesgo, plan de tratamiento y seguimiento de riesgo residual. |
| MOD·SOA | SoA · Anexo A | 1 | Declaración de Aplicabilidad sobre los 93 controles de ISO/IEC 27001:2022 en 4 temas, con justificación de exclusión y dueño por control. |
| MOD·AUD | Auditoría interna | 1 | Programa anual, checklists por dominio, hallazgos clasificados, no conformidades y acciones correctivas (CAPA) con cierre verificable. |
| MOD·WZD | Asistente paso a paso | 1 | Convierte la metodología de la sección 02 en tareas asignadas, con fecha, responsable y evidencia requerida por fase — el corazón de la propuesta frente a una hoja de cálculo. |
| MOD·KPI | Indicadores y revisión | 1 | Tableros de cumplimiento por dominio y por tenant, minutas de revisión por la dirección, exportables como registro auditable. |
| MOD·TRN | Capacitación y cultura | 1 | Campañas de concientización, acuse de políticas, registros de competencia y reporte de incidentes desde el colaborador. |
| MOD·NIST | Módulo NIST CSF 2.0 | 2 | Gobernar, Identificar, Proteger, Detectar, Responder, Recuperar — mapeado a los mismos controles ya cargados por ISO, sin doble captura de evidencia. |

## 02 · Metodología paso a paso — Ocho fases, un ciclo que no termina

Esto es lo que un cliente ve al iniciar: no un tablero vacío, sino un camino.
Cada fase abre tareas concretas y pide evidencia específica antes de dejar
avanzar a la siguiente; al llegar a la fase 8, el ciclo vuelve a la 1 como
mejora continua, no como reinicio.

```
01 Diagnóstico inicial   → Brechas vs Anexo A
02 Contexto y alcance    → Límites del SGSI
03 Liderazgo y política  → Compromiso directivo
04 Riesgos y tratamiento → Matriz y plan
05 SoA y controles       → 93 controles Anexo A
06 Implementación        → Con evidencia real
07 Auditoría interna     → Hallazgos y CAPA
08 Revisión y certificación → Con auditor externo
   └──────────────────────────────────────┘
         (vuelve al paso 01 · PDCA)
```

El asistente paso a paso (MOD·WZD) convierte estas ocho fases en tareas con
dueño y evidencia. El mismo esqueleto — diagnóstico, contexto, gobierno,
riesgo, controles, implementación, verificación, revisión — se reutiliza en
la Fase 2 para guiar la adopción de NIST CSF.

## 03 · Motor de frameworks — Por qué NIST no obliga a rehacer el modelo

La tentación natural es modelar tablas `iso_control`, `iso_riesgo`,
`iso_evidencia`. Eso funciona para la Fase 1 y se vuelve una migración
dolorosa en la Fase 2. En su lugar, **un framework es un dato, no un
esquema**: ISO 27001 y NIST CSF cargan sus dominios y controles como filas
sobre las mismas tablas de `Dominio → Control → Requisito`.

```
ISO/IEC 27001:2022 ─┐              ┌─→ Riesgos    (matriz y plan de tratamiento)
 4 temas · 93 ctrl   ├─ se normaliza en ─→ Motor de frameworks
NIST CSF 2.0 ────────┘   (Dominio→Control→Requisito,   ├─→ Evidencia   (archivo, enlace o registro)
 Fase 2 · hoja de ruta     tabla de datos, no de esquema) └─→ Auditoría   (hallazgos → CAPA)
                                                              Evidencia se registra como
                                                              Documento (MOD·DOC)
```

Cargar NIST CSF 2.0 en la Fase 2 es una operación de datos — nuevas filas de
dominio y control — no una migración de esquema ni un segundo módulo de
evidencia paralelo.

## 04 · Multi-tenencia — Un solo plano de aplicación, dos niveles de aislamiento

No todos los tenants necesitan lo mismo: una pyme certificándose por primera
vez no tiene el mismo requisito de aislamiento que un banco o una entidad de
salud. TridentyAuditor resuelve esto en la capa de datos, no en la de
aplicación — el mismo código de negocio, empaquetado como los mismos
contenedores, atiende ambos niveles.

| | Tier **pooled** — Pyme / Estándar | Tier **aislado** — Enterprise / Regulado |
|---|---|---|
| Datos | PostgreSQL compartido, Row-Level Security por `tenant_id` | PostgreSQL dedicado, instancia o clúster propio por tenant |
| Storage/secretos | Object Storage S3-compatible, bucket lógico por tenant | Storage y secretos dedicados, llave propia (BYOK opcional) |
| Perfil | Alta densidad, costo optimizado, SGSI en implementación inicial | Aislamiento físico y residencia de datos, incluso en clúster propio del cliente |

La solicitud del tenant llega con un JWT (`tenant_id`/dominio) que resuelve
un middleware stateless (Tenant Resolver) sobre el mismo Helm chart. El
nivel de aislamiento se decide por tenant al momento del alta comercial, no
al momento del deploy — la migración de pooled a aislado es una operación de
datos entre dos clústeres PostgreSQL, no un cambio de plataforma. El tier
aislado entra en producción en la Fase 2, junto con el módulo NIST, y puede
desplegarse tanto en la nube de Netmask como dentro del centro de datos del
cliente.

## 05 · Arquitectura en contenedores — De la petición del navegador al dato en reposo

Una sola ruta de petición atraviesa borde, API y aplicación; identidad,
observabilidad y continuidad son transversales — no viven en el camino
crítico de cada request. Cada capa es un componente de código abierto
empaquetado como contenedor OCI, así que el clúster puede vivir en Azure
(AKS), en cualquier otra nube o en el centro de datos de un cliente.

```
Cliente web (por tenant)
        │
Ingress + WAF (NGINX/Traefik)         TLS · mitigación básica · enrutamiento
        │
API Gateway (Kong/Traefik)  ←···· Keycloak (SSO/SAML/OIDC · MFA)
        │                    ···→ Prometheus+Grafana (métricas, logs, trazas)
Clúster Kubernetes
microservicios TridentyAuditor · autoescalado · cualquier nube
        │
   ┌────┼────────────┬──────────────────┐
PostgreSQL   Object Storage      Vault/Secrets      RabbitMQ/NATS
compartido+  S3-compatible       Manager            async · notificaciones
dedicado,RLS (WORM)+OpenSearch   llaves por tenant
   │
Velero + réplica de almacenamiento (continuidad y recuperación / DR)
```

**Mismo Helm chart, cualquier clúster:** el empaquetado en contenedores mueve
la elección de nube de una decisión de arquitectura a una decisión
comercial. El mismo paquete de manifiestos se despliega sin cambios en AKS
(Azure), EKS (AWS), GKE (Google Cloud), OpenShift on-prem o k3s en el
clúster del cliente.

### Componentes y su propósito

| Capa | Componente / tecnología | Propósito en TridentyAuditor |
|---|---|---|
| Borde y perímetro | Ingress Controller (NGINX/Traefik) + WAF | TLS, mitigación de ataques comunes, enrutamiento por tenant |
| API Gateway | Kong / Traefik / Gloo | Auth de API, throttling por tenant, versionado de contratos |
| Identidad | Keycloak (OIDC/SAML) | SSO por tenant, MFA, federación con el AD/Entra del cliente si aplica |
| Orquestación | Kubernetes (AKS, EKS, GKE, on-prem, k3s) | Backend modular en contenedores OCI, autoescalado horizontal |
| Datos relacionales | PostgreSQL (gestionado o autoalojado) | Row-Level Security por tenant, instancia dedicada en tier aislado |
| Documentos y evidencia | Object Storage S3-compatible + OpenSearch | Repositorio documental, búsqueda full-text, política WORM |
| Secretos y llaves | HashiCorp Vault / External Secrets Operator | Gestión de llaves por tenant, BYOK opcional para tier aislado |
| Mensajería | RabbitMQ o NATS (Kafka si el volumen lo exige) | Notificaciones, recordatorios de auditoría, integración por eventos |
| Observabilidad | Prometheus + Grafana + Loki/Tempo (OpenTelemetry) | Métricas, logs y trazas; exportable a un SIEM externo del cliente |
| Continuidad | Velero + réplica de almacenamiento entre nubes | Backup de clúster y datos, restauración cruzada, soporte a A.5.29/A.5.30 |
| CI/CD | GitHub Actions o GitLab CI + Argo CD | Build de imágenes OCI firmadas, despliegue por GitOps |

## 06 · Seguridad de la plataforma — La herramienta de auditoría también se audita

Un SGSI-como-servicio que no puede sostener su propia auditoría es un
problema de credibilidad, no solo técnico. Compromisos concretos:

- **Cifrado en tránsito y en reposo:** TLS 1.2+ de extremo a extremo; cifrado
  en reposo con llaves administradas por Vault, con llave propia por tenant
  en el tier aislado.
- **Evidencia inmutable:** política WORM sobre el almacenamiento de objetos
  para evidencia una vez aprobada; ningún rol, incluido el de soporte de
  Netmask, puede editar un registro publicado.
- **Bitácora de auditoría propia:** cada lectura y escritura sobre
  evidencia, control o hallazgo queda registrada de forma append-only — la
  plataforma es su propio primer cliente.
- **Aislamiento verificable:** Row-Level Security probada por prueba
  automatizada en cada despliegue; el tier aislado se valida además con
  pruebas de penetración por tenant regulado.
- **Residencia de datos:** selección de región, nube o incluso centro de
  datos por tenant, cuando el contrato o la regulación local lo exija.
- **Continuidad:** RPO/RTO definidos por tier, con réplica entre nubes para
  el tier aislado y restauración probada trimestralmente.
- **Cadena de suministro de contenedores:** imágenes escaneadas y firmadas
  (Trivy, cosign/Sigstore) antes de publicarse; políticas de admisión
  (OPA/Kyverno) bloquean lo que no cumple en el clúster.

> Meta de producto: que la operación de TridentyAuditor, en cualquier nube o
> centro de datos que la aloje, sea ella misma un candidato razonable a
> certificación ISO/IEC 27001 — no solo la herramienta que la vende.

## 07 · Roles y permisos — Quién ve qué, y por qué eso importa en un SaaS multitenant

El límite más delicado no es entre roles dentro de un tenant, sino entre
Netmask y sus clientes: soporte de Netmask no tiene acceso de lectura a
contenido de un tenant salvo autorización explícita y con registro.

| Rol | Alcance | Permisos clave |
|---|---|---|
| Super Admin Netmask | Cross-tenant | Aprovisionar tenants, monitoreo global; sin acceso a documentos de cliente salvo soporte autorizado y auditado |
| Admin del tenant (CISO / líder SGSI) | Todo el tenant | Configura el SGSI, gestiona usuarios, aprueba política, visibilidad total |
| Dueño de control | Dominio(s) asignado(s) | Carga evidencia, actualiza estado de implementación y plan de tratamiento |
| Auditor interno | Tenant, módulo de auditoría | Programa de auditoría, checklists, hallazgos, seguimiento de CAPA |
| Auditor externo / certificador | Acceso temporal, solo lectura | Evidencia del alcance de la auditoría, exportación con marca de agua y expiración |
| Colaborador | Tenant, limitado | Capacitación, reporte de incidentes, acuse de política |
| Dirección / ejecutivo | Tenant, tableros | Indicadores y revisión por la dirección, sin permisos de edición |

## 08 · Hoja de ruta — Tres fases, un mismo núcleo

**Fase 1 · 0–6 meses — Núcleo ISO 27001**
- Control documental, riesgos, SoA y auditoría interna
- Asistente paso a paso (8 fases)
- Tier pooled multitenant en contenedores (MVP)
- Helm chart inicial: API + PostgreSQL + object storage

**Fase 2 · 6–12 meses — NIST CSF y tier aislado**
- Módulo NIST CSF 2.0 sobre el motor de frameworks
- Tier aislado para clientes regulados, desplegable en su propio clúster
- SSO empresarial (Keycloak, federado con el IdP del cliente)
- Stack de observabilidad propio, exportable a un SIEM externo

**Fase 3 · 12+ meses — Expansión multi-framework**
- ISO 27701 (privacidad), SOC 2, ISO 9001
- Marketplace de integraciones (SIEM, ITSM, HRIS)
- Asistencia por IA para redacción de evidencia y políticas

## 09 · Frente a herramientas de referencia

Qué cambia frente a un SGSI llevado en Kawak o en hojas de cálculo:

| Capacidad | Enfoque tradicional | TridentyAuditor |
|---|---|---|
| Aislamiento de datos | Una instancia por cliente, gestionada a mano | Multitenant nativo, con tier dedicado configurable por contrato |
| Cobertura de frameworks | Esquema fijo para un estándar | Motor de frameworks: ISO hoy, NIST en Fase 2, sin migración de esquema |
| Evidencia | Adjuntos sueltos, versión por nombre de archivo | Evidencia versionada e inmutable, trazable a control y a hallazgo |
| Despliegue | On-premise fijo o instancia dedicada por cliente, difícil de mover | Contenedores portables: SaaS multitenant o, para el tier aislado, el mismo Helm chart en el clúster del cliente |
| Actualización de controles | Manual, por revisión de plantilla | Cambia una fila del motor de frameworks; se propaga a todos los tenants en ese framework |
