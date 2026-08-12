"""Seed data for ISO/IEC 27001:2022 Annex A — 4 themes, 93 controles.

Solo se cargan los identificadores y títulos oficiales del tema/control (la
taxonomía en sí, ampliamente publicada como índice de referencia) más una
guía práctica de evidencia redactada por el equipo. El texto normativo
completo del estándar es contenido licenciado y sigue sin reproducirse aquí
a propósito — los tenants documentan su propia interpretación/evidencia por
control vía MOD·DOC, y la tabla ``requirements`` sigue disponible para ese
texto si se carga una copia licenciada más adelante.

La guía de evidencia (``evidence_guidance``) tampoco es texto del estándar:
es una lista de ejemplos de qué documento/artefacto suele demostrar el
control en la práctica, pensada como punto de partida para el equipo que
está armando su carpeta de auditoría — no reemplaza el criterio del auditor
ni es la única evidencia válida.
"""

from sqlalchemy.orm import Session

from app.frameworks.models import Control, Domain, Framework

FRAMEWORK_CODE = "ISO27001:2022"
FRAMEWORK_NAME = "ISO/IEC 27001:2022"
FRAMEWORK_VERSION = "2022"

# domain code -> (name, [(control code, name, evidence_guidance), ...])
DOMAINS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    (
        "A.5",
        "Controles organizacionales",
        [
            (
                "A.5.1",
                "Policies for information security",
                "Política de seguridad de la información aprobada por la dirección (fecha, versión, "
                "acta o firma de aprobación) y evidencia de su publicación o socialización al personal.",
            ),
            (
                "A.5.2",
                "Information security roles and responsibilities",
                "Matriz de roles y responsabilidades de seguridad (RACI), organigrama del SGSI y actas "
                "de nombramiento o aceptación del rol.",
            ),
            (
                "A.5.3",
                "Segregation of duties",
                "Matriz de segregación de funciones o análisis de conflicto de roles en sistemas "
                "críticos (quién solicita vs. quién aprueba vs. quién ejecuta).",
            ),
            (
                "A.5.4",
                "Management responsibilities",
                "Comunicado o cláusula donde la dirección exige el cumplimiento de las políticas de "
                "seguridad al personal (ej. incluido en la inducción o el contrato).",
            ),
            (
                "A.5.5",
                "Contact with authorities",
                "Listado de autoridades relevantes (policía, CSIRT nacional, protección de datos) con "
                "datos de contacto y evidencia de comunicación (correos, actas).",
            ),
            (
                "A.5.6",
                "Contact with special interest groups",
                "Listado de membresías o participación en foros/grupos de seguridad (ISACs, comunidades "
                "técnicas) y evidencia de participación (boletines, actas).",
            ),
            (
                "A.5.7",
                "Threat intelligence",
                "Fuentes de inteligencia de amenazas suscritas (feeds, boletines de CERT) y registro de "
                "alertas o análisis procesados.",
            ),
            (
                "A.5.8",
                "Information security in project management",
                "Checklist de seguridad incluido en la metodología de gestión de proyectos, con "
                "evidencia de su aplicación en un proyecto reciente.",
            ),
            (
                "A.5.9",
                "Inventory of information and other associated assets",
                "Inventario de activos de información actualizado (hoja de cálculo o CMDB) con dueño, "
                "clasificación y ubicación.",
            ),
            (
                "A.5.10",
                "Acceptable use of information and other associated assets",
                "Política de uso aceptable firmada o aceptada por los usuarios (ej. en la inducción o "
                "en el sistema de RRHH).",
            ),
            (
                "A.5.11",
                "Return of assets",
                "Formato de devolución de activos al finalizar el contrato (checklist firmado en el "
                "proceso de offboarding).",
            ),
            (
                "A.5.12",
                "Classification of information",
                "Esquema de clasificación de la información (ej. pública/interna/confidencial/"
                "restringida) y ejemplo de documentos etiquetados según ese esquema.",
            ),
            (
                "A.5.13",
                "Labelling of information",
                "Evidencia de etiquetado (metadatos, marcas de agua, encabezados) en documentos o "
                "repositorios según su clasificación.",
            ),
            (
                "A.5.14",
                "Information transfer",
                "Procedimiento o acuerdo de transferencia segura de información (cifrado en tránsito, "
                "acuerdos con terceros) y registro de transferencias críticas.",
            ),
            (
                "A.5.15",
                "Access control",
                "Política de control de acceso aprobada y matriz de accesos por rol/sistema.",
            ),
            (
                "A.5.16",
                "Identity management",
                "Procedimiento de gestión del ciclo de vida de identidades (alta/baja/cambio) y "
                "ticket de una alta o baja reciente.",
            ),
            (
                "A.5.17",
                "Authentication information",
                "Política de gestión de contraseñas/credenciales y captura de la configuración que la "
                "hace cumplir (complejidad, expiración).",
            ),
            (
                "A.5.18",
                "Access rights",
                "Registro de revisión periódica de accesos (certificación de accesos) firmado por los "
                "dueños de la información.",
            ),
            (
                "A.5.19",
                "Information security in supplier relationships",
                "Procedimiento de evaluación de seguridad de proveedores y evidencia de una evaluación "
                "aplicada (cuestionario, informe).",
            ),
            (
                "A.5.20",
                "Addressing information security within supplier agreements",
                "Cláusulas de seguridad incluidas en un contrato o acuerdo de nivel de servicio con un "
                "proveedor (extracto del contrato).",
            ),
            (
                "A.5.21",
                "Managing information security in the ICT supply chain",
                "Evaluación de riesgo de la cadena de suministro de TI (subcontratistas, componentes de "
                "software) y registro de mitigaciones aplicadas.",
            ),
            (
                "A.5.22",
                "Monitoring, review and change management of supplier services",
                "Informe de revisión periódica del desempeño/seguridad de un proveedor (KPI, auditoría, "
                "encuesta) y registro de cambios notificados por el proveedor.",
            ),
            (
                "A.5.23",
                "Information security for use of cloud services",
                "Política de uso de servicios en la nube y evidencia de evaluación de seguridad del "
                "proveedor cloud contratado (certificaciones, configuración de seguridad).",
            ),
            (
                "A.5.24",
                "Information security incident management planning and preparation",
                "Plan de respuesta a incidentes aprobado, con roles y canales de escalamiento, y "
                "evidencia de una prueba o simulacro.",
            ),
            (
                "A.5.25",
                "Assessment and decision on information security events",
                "Bitácora de eventos de seguridad evaluados con la decisión tomada (si se clasificó o "
                "no como incidente).",
            ),
            (
                "A.5.26",
                "Response to information security incidents",
                "Registro de un incidente gestionado de principio a fin (detección, contención, "
                "erradicación, cierre) con línea de tiempo.",
            ),
            (
                "A.5.27",
                "Learning from information security incidents",
                "Informe de lecciones aprendidas o post-mortem de un incidente, con acciones de mejora "
                "derivadas.",
            ),
            (
                "A.5.28",
                "Collection of evidence",
                "Procedimiento de cadena de custodia de evidencia digital y un caso de recolección "
                "aplicado (hash, actas).",
            ),
            (
                "A.5.29",
                "Information security during disruption",
                "Plan de continuidad de seguridad de la información durante una disrupción, incluido "
                "en el BCP/DRP.",
            ),
            (
                "A.5.30",
                "ICT readiness for business continuity",
                "Plan de recuperación de TI (DRP) y resultados de una prueba de recuperación (RTO/RPO "
                "logrados vs. objetivo).",
            ),
            (
                "A.5.31",
                "Legal, statutory, regulatory and contractual requirements",
                "Matriz de requisitos legales y contractuales aplicables (protección de datos, "
                "sectoriales, contratos) con su estado de cumplimiento.",
            ),
            (
                "A.5.32",
                "Intellectual property rights",
                "Registro de licencias de software adquiridas/vigentes y procedimiento de verificación "
                "de cumplimiento de licenciamiento.",
            ),
            (
                "A.5.33",
                "Protection of records",
                "Política de retención y protección de registros, con evidencia de controles aplicados "
                "(backup, control de acceso, retención documental).",
            ),
            (
                "A.5.34",
                "Privacy and protection of PII",
                "Registro de actividades de tratamiento de datos personales (RAT) y evidencia de "
                "medidas de protección aplicadas (cifrado, anonimización, avisos de privacidad).",
            ),
            (
                "A.5.35",
                "Independent review of information security",
                "Informe de una revisión/auditoría independiente del SGSI (interna con otro equipo o "
                "externa) con hallazgos y fecha.",
            ),
            (
                "A.5.36",
                "Compliance with policies, rules and standards for information security",
                "Informe de verificación de cumplimiento interno que compare la operación real contra "
                "las políticas vigentes.",
            ),
            (
                "A.5.37",
                "Documented operating procedures",
                "Procedimientos operativos documentados y aprobados para actividades críticas de TI/"
                "seguridad (gestión de cambios, backups, hardening).",
            ),
        ],
    ),
    (
        "A.6",
        "Controles de personas",
        [
            (
                "A.6.1",
                "Screening",
                "Evidencia de verificación de antecedentes al contratar (certificado judicial, "
                "referencias, verificación de estudios) según la política de RRHH.",
            ),
            (
                "A.6.2",
                "Terms and conditions of employment",
                "Cláusulas de seguridad de la información incluidas en el contrato laboral, firmadas "
                "por el colaborador.",
            ),
            (
                "A.6.3",
                "Information security awareness, education and training",
                "Plan anual de concientización, material de capacitación y registro de "
                "asistencia/evaluación del personal.",
            ),
            (
                "A.6.4",
                "Disciplinary process",
                "Procedimiento disciplinario formal para violaciones de seguridad, referenciado en el "
                "reglamento interno de trabajo.",
            ),
            (
                "A.6.5",
                "Responsibilities after termination or change of employment",
                "Checklist de offboarding/cambio de cargo con revocación de accesos y recordatorio de "
                "obligaciones de confidencialidad post-contractuales.",
            ),
            (
                "A.6.6",
                "Confidentiality or non-disclosure agreements",
                "Acuerdo de confidencialidad (NDA) firmado por empleados, contratistas o terceros con "
                "acceso a información sensible.",
            ),
            (
                "A.6.7",
                "Remote working",
                "Política de trabajo remoto con controles técnicos exigidos (VPN, cifrado, dispositivo "
                "autorizado) y evidencia de su aplicación.",
            ),
            (
                "A.6.8",
                "Information security event reporting",
                "Canal formal de reporte de eventos de seguridad (correo, formulario, línea) y registro "
                "de reportes recibidos del personal.",
            ),
        ],
    ),
    (
        "A.7",
        "Controles físicos",
        [
            (
                "A.7.1",
                "Physical security perimeters",
                "Planos o descripción de los perímetros de seguridad física (cercas, muros, puertas de "
                "acceso controlado) de las instalaciones.",
            ),
            (
                "A.7.2",
                "Physical entry",
                "Registro de control de acceso físico (bitácora, logs de tarjetas/biometría) a las "
                "instalaciones o áreas restringidas.",
            ),
            (
                "A.7.3",
                "Securing offices, rooms and facilities",
                "Evidencia de controles físicos en oficinas/salas críticas (cerraduras, control de "
                "acceso, cámaras) — fotos o ficha técnica.",
            ),
            (
                "A.7.4",
                "Physical security monitoring",
                "Registro de monitoreo de CCTV/alarmas de las instalaciones, con política de retención.",
            ),
            (
                "A.7.5",
                "Protecting against physical and environmental threats",
                "Evaluación de riesgos ambientales (incendio, inundación) y evidencia de controles "
                "instalados (extintores, detectores de humo, mantenimiento).",
            ),
            (
                "A.7.6",
                "Working in secure areas",
                "Procedimiento de trabajo en áreas seguras (centro de datos, cuartos de comunicaciones) "
                "con registro de accesos autorizados.",
            ),
            (
                "A.7.7",
                "Clear desk and clear screen",
                "Política de escritorio y pantalla limpios, y evidencia de verificación (auditoría "
                "visual, encuesta) de su cumplimiento.",
            ),
            (
                "A.7.8",
                "Equipment siting and protection",
                "Evidencia de ubicación y protección de equipos críticos (racks, UPS, control de "
                "temperatura) — inspección o inventario de sala técnica.",
            ),
            (
                "A.7.9",
                "Security of assets off-premises",
                "Procedimiento y registro de autorización para sacar equipos de las instalaciones (ej. "
                "formato de préstamo de portátil).",
            ),
            (
                "A.7.10",
                "Storage media",
                "Procedimiento de gestión de medios removibles (USB, discos) incluyendo cifrado y "
                "control de uso, con registro de medios autorizados.",
            ),
            (
                "A.7.11",
                "Supporting utilities",
                "Evidencia de mantenimiento de servicios de soporte (energía, UPS, generador, aire "
                "acondicionado) — contratos de mantenimiento, bitácoras.",
            ),
            (
                "A.7.12",
                "Cabling security",
                "Evidencia de protección del cableado eléctrico y de datos (canaletas, separación, "
                "planos) frente a interceptación o daño.",
            ),
            (
                "A.7.13",
                "Equipment maintenance",
                "Registro o contrato de mantenimiento preventivo y correctivo de equipos, con fechas y "
                "responsable.",
            ),
            (
                "A.7.14",
                "Secure disposal or re-use of equipment",
                "Certificado de borrado seguro o destrucción física de medios de almacenamiento dados "
                "de baja.",
            ),
        ],
    ),
    (
        "A.8",
        "Controles tecnológicos",
        [
            (
                "A.8.1",
                "User endpoint devices",
                "Política de uso de dispositivos de usuario final y evidencia de controles técnicos "
                "aplicados (MDM, cifrado de disco, antivirus).",
            ),
            (
                "A.8.2",
                "Privileged access rights",
                "Inventario de cuentas privilegiadas y procedimiento de aprobación/revisión periódica "
                "de accesos administrativos.",
            ),
            (
                "A.8.3",
                "Information access restriction",
                "Captura de la matriz de permisos por rol en un sistema crítico que demuestre "
                "restricción según necesidad de conocer.",
            ),
            (
                "A.8.4",
                "Access to source code",
                "Configuración de control de acceso al repositorio de código fuente (permisos por rol "
                "en el sistema de control de versiones).",
            ),
            (
                "A.8.5",
                "Secure authentication",
                "Configuración de autenticación multifactor (MFA) en sistemas críticos — capturas de "
                "política o reporte del proveedor de identidad.",
            ),
            (
                "A.8.6",
                "Capacity management",
                "Reporte de monitoreo de capacidad (CPU, almacenamiento, red) y plan de crecimiento o "
                "alertas configuradas.",
            ),
            (
                "A.8.7",
                "Protection against malware",
                "Consola o reporte de la solución antimalware mostrando cobertura, actualizaciones y "
                "detecciones gestionadas.",
            ),
            (
                "A.8.8",
                "Management of technical vulnerabilities",
                "Informe de escaneo de vulnerabilidades reciente y registro de remediación (tickets "
                "cerrados) según el SLA definido.",
            ),
            (
                "A.8.9",
                "Configuration management",
                "Líneas base de configuración segura (hardening) documentadas y evidencia de aplicación "
                "(ej. reporte de cumplimiento de un benchmark CIS).",
            ),
            (
                "A.8.10",
                "Information deletion",
                "Procedimiento de eliminación segura de información al finalizar su uso/retención, con "
                "registro de una eliminación ejecutada.",
            ),
            (
                "A.8.11",
                "Data masking",
                "Evidencia de enmascaramiento/anonimización de datos sensibles en ambientes no "
                "productivos (capturas antes/después o configuración de la herramienta).",
            ),
            (
                "A.8.12",
                "Data leakage prevention",
                "Configuración o reporte de la herramienta de prevención de fuga de datos (DLP) con "
                "reglas activas e incidentes gestionados.",
            ),
            (
                "A.8.13",
                "Information backup",
                "Política de copias de respaldo y reporte de ejecución/restauración exitosa de un "
                "backup (prueba de restauración).",
            ),
            (
                "A.8.14",
                "Redundancy of information processing facilities",
                "Diseño de arquitectura con redundancia (failover, balanceo) y evidencia de una prueba "
                "de conmutación.",
            ),
            (
                "A.8.15",
                "Logging",
                "Configuración de generación de logs en sistemas críticos y muestra de un log con los "
                "eventos mínimos requeridos (acceso, cambios, errores).",
            ),
            (
                "A.8.16",
                "Monitoring activities",
                "Reporte o dashboard de la herramienta de monitoreo/SIEM mostrando alertas revisadas en "
                "un periodo reciente.",
            ),
            (
                "A.8.17",
                "Clock synchronization",
                "Configuración del servicio de sincronización horaria (NTP) en los servidores/sistemas "
                "críticos.",
            ),
            (
                "A.8.18",
                "Use of privileged utility programs",
                "Inventario de utilitarios privilegiados autorizados y evidencia de restricción de su "
                "uso (control de acceso, registro de uso).",
            ),
            (
                "A.8.19",
                "Installation of software on operational systems",
                "Procedimiento de control de instalación de software en producción y registro de una "
                "instalación autorizada.",
            ),
            (
                "A.8.20",
                "Networks security",
                "Diagrama de red con zonas de seguridad y evidencia de controles perimetrales (firewall, "
                "reglas activas).",
            ),
            (
                "A.8.21",
                "Security of network services",
                "Acuerdo o especificación de seguridad de servicios de red contratados a terceros (ISP, "
                "proveedor de conectividad).",
            ),
            (
                "A.8.22",
                "Segregation of networks",
                "Diagrama o configuración de segmentación de red (VLANs, zonas DMZ) que separe "
                "ambientes según criticidad.",
            ),
            (
                "A.8.23",
                "Web filtering",
                "Configuración o reporte de la herramienta de filtrado web mostrando categorías "
                "bloqueadas y excepciones.",
            ),
            (
                "A.8.24",
                "Use of cryptography",
                "Política de uso de cifrado (algoritmos y longitudes de llave aprobados) y evidencia de "
                "su aplicación (certificados, configuración TLS).",
            ),
            (
                "A.8.25",
                "Secure development life cycle",
                "Metodología de desarrollo seguro (SDLC) documentada, con las actividades de seguridad "
                "integradas por fase.",
            ),
            (
                "A.8.26",
                "Application security requirements",
                "Checklist de requisitos de seguridad aplicado en un proyecto de desarrollo/adquisición "
                "reciente.",
            ),
            (
                "A.8.27",
                "Secure system architecture and engineering principles",
                "Principios de arquitectura segura documentados (defensa en profundidad, mínimo "
                "privilegio) y evidencia de aplicación en un diseño reciente.",
            ),
            (
                "A.8.28",
                "Secure coding",
                "Estándar de codificación segura y resultado de un análisis estático de código (SAST) "
                "sobre un repositorio.",
            ),
            (
                "A.8.29",
                "Security testing in development and acceptance",
                "Informe de pruebas de seguridad (pentest, SAST/DAST) ejecutado antes del paso a "
                "producción de una aplicación.",
            ),
            (
                "A.8.30",
                "Outsourced development",
                "Cláusulas de seguridad en el contrato de desarrollo tercerizado y evidencia de revisión "
                "de seguridad del entregable.",
            ),
            (
                "A.8.31",
                "Separation of development, test and production environments",
                "Evidencia de separación de ambientes (accesos, redes o infraestructura distinta) entre "
                "desarrollo, pruebas y producción.",
            ),
            (
                "A.8.32",
                "Change management",
                "Procedimiento de gestión de cambios y registro de un cambio (solicitud, aprobación, "
                "prueba, despliegue) en el sistema de tickets.",
            ),
            (
                "A.8.33",
                "Test information",
                "Procedimiento de protección de datos usados en pruebas (enmascaramiento o datos "
                "sintéticos) y evidencia de su aplicación.",
            ),
            (
                "A.8.34",
                "Protection of information systems during audit testing",
                "Plan de una auditoría/prueba técnica que incluya medidas para minimizar el impacto en "
                "sistemas productivos (ventanas de mantenimiento, respaldo previo).",
            ),
        ],
    ),
]


def seed_iso27001(db: Session) -> Framework:
    """Idempotent seed: safe to call on every startup/migración.

    Inserta lo que falte y también actualiza ``name``/``evidence_guidance``
    de los dominios y controles ya existentes, para que revisar o ampliar la
    guía de evidencia en este archivo se refleje en despliegues que ya
    habían sembrado el framework antes.
    """
    framework = db.query(Framework).filter_by(code=FRAMEWORK_CODE).one_or_none()
    if framework is None:
        framework = Framework(code=FRAMEWORK_CODE, name=FRAMEWORK_NAME, version=FRAMEWORK_VERSION)
        db.add(framework)
        db.flush()

    for domain_order, (domain_code, domain_name, controls) in enumerate(DOMAINS):
        domain = (
            db.query(Domain)
            .filter_by(framework_id=framework.id, code=domain_code)
            .one_or_none()
        )
        if domain is None:
            domain = Domain(
                framework_id=framework.id,
                code=domain_code,
                name=domain_name,
                order_index=domain_order,
            )
            db.add(domain)
            db.flush()
        else:
            domain.name = domain_name
            domain.order_index = domain_order

        for control_order, (control_code, control_name, evidence_guidance) in enumerate(controls):
            existing = (
                db.query(Control)
                .filter_by(domain_id=domain.id, code=control_code)
                .one_or_none()
            )
            if existing is None:
                db.add(
                    Control(
                        domain_id=domain.id,
                        code=control_code,
                        name=control_name,
                        evidence_guidance=evidence_guidance,
                        order_index=control_order,
                    )
                )
            else:
                existing.name = control_name
                existing.evidence_guidance = evidence_guidance
                existing.order_index = control_order

    db.commit()
    return framework
