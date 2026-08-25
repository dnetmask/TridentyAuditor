"""Seed data for la Guía de Ciberseguridad del CNO (Acuerdo 1960) — sector eléctrico
colombiano, 10 numerales normativos y 41 controles.

Fuente: Anexo 1 (Guía de Ciberseguridad), Anexo 2 (Criterios de activos
críticos) y Anexo 3 (Lista de cumplimiento periódico) del Acuerdo 1960 del
Consejo Nacional de Operación (CNO), 3 de abril de 2025. Es texto regulatorio
público colombiano — a diferencia de ISO/IEC 27001:2022 (ver
``iso27001_2022.py``), aquí no hay contenido licenciado que reproducir, así
que este seed sí carga la tabla ``requirements`` con cada ítem de evidencia
del Anexo 3 (varios controles traen 2 o más), no solo el control.

Los numerales 1 (introducción/glosario) y 2 (ámbito de aplicación) del Anexo 1
no traen controles propios en el Anexo 3 y no se siembran como dominios —
el motor empieza en el numeral 3 (Cumplimiento), que es donde arranca la
lista de cumplimiento real.

Dos columnas del Anexo 3 quedan deliberadamente fuera de ``evidence_guidance``:
"Propuesta prórroga" son plazos de transición del Acuerdo 1960 sobre el
Acuerdo 1502 anterior (fechas fijas 2026-2028) — información de este año,
no una guía permanente de cómo demostrar el control. "Aplicabilidad plantas
menores" sí se conserva, como una frase al final de la guía cuando aplica.
"""

from sqlalchemy.orm import Session

from app.frameworks.models import Control, Domain, Framework, Requirement

FRAMEWORK_CODE = "CNO-1960"
FRAMEWORK_NAME = "Guía de Ciberseguridad — Consejo Nacional de Operación (CNO)"
FRAMEWORK_VERSION = "Acuerdo 1960 · 2025"

# domain code -> (name, [(control code, name, evidence_guidance, [(req code, req text), ...]), ...])
DOMAINS = [   (   '3',
        'Cumplimiento',
        [   (   '3.1',
                'Auditorías',
                'Reportes de auditorías internas. Periodicidad: cada 24 meses. Aplica también a '
                'los agentes generadores con plantas menores.',
                [('3.1-1', 'Reportes de auditorías internas. (periodicidad: cada 24 meses)')])]),
    (   '4',
        'Identificación de activos críticos',
        [   (   '4.1',
                'Activos críticos',
                'Realizar la lista, actualización o revisión de activos y ciberactivos críticos '
                'con la aprobación por parte de la entidad. Para las plantas menores es el '
                'inventario de ciberactivos. Periodicidad: cada 12 meses.',
                [   (   '4.1-1',
                        'Realizar la lista, actualización o revisión de activos y ciberactivos '
                        'críticos con la aprobación por parte de la entidad. Para las plantas '
                        'menores es el inventario de ciberactivos. (periodicidad: cada 12 '
                        'meses)')]),
            (   '4.2',
                'Ciberactivos críticos',
                'Inventario de ciberactivos críticos identificados a partir de los activos '
                'críticos del numeral 4.1, con la información que permita identificar de forma '
                'única cada ciberactivo en la red y el activo crítico al que pertenece. Aplica '
                'también a los agentes generadores con plantas menores.',
                [   (   '4.2-1',
                        'Inventario de ciberactivos críticos identificado a partir de los '
                        'activos críticos del numeral 4.1 (periodicidad: junto con la revisión '
                        'de activos críticos del numeral 4.1)')])]),
    (   '5',
        'Gobierno y gestión del personal',
        [   (   '5.1',
                'Política y lineamiento de ciberseguridad',
                'Documento política o lineamiento de ciberseguridad. Periodicidad: cada vez que '
                'se requiera. Aplica también a los agentes generadores con plantas menores.',
                [   (   '5.1-1',
                        'Documento política o lineamiento de ciberseguridad. (periodicidad: cada '
                        'vez que se requiera)')]),
            (   '5.2',
                'Responsable de ciberseguridad',
                'Documento de asignación o delegación enviado al CNO donde se evidencie el '
                'responsable de ciberseguridad. Periodicidad: cada vez que se actualice y máximo '
                '20 días calendario.',
                [   (   '5.2-1',
                        'Documento de asignación o delegación enviado al CNO donde se evidencie '
                        'el responsable de ciberseguridad. (periodicidad: cada vez que se '
                        'actualice y máximo 20 días calendario)')]),
            (   '5.3',
                'Evaluación de riesgos para el personal',
                'Evidencia esperada: Evaluación de riesgos realizado al personal de la entidad. '
                '(máximo 20 días de causarse la novedad de personal); Certificación por parte de '
                'proveedores y contratistas sobre la evaluación de riesgos a su personal. (al '
                'inicio del contrato y que tenga vigencia durante la duración del contrato); '
                'Actualización de la evaluación de riesgos cada persona que tenga acceso físico '
                'o lógico a activos o ciberactivos críticos. (cada 24 meses).',
                [   (   '5.3-1',
                        'Evaluación de riesgos realizado al personal de la entidad. '
                        '(periodicidad: máximo 20 días de causarse la novedad de personal)'),
                    (   '5.3-2',
                        'Certificación por parte de proveedores y contratistas sobre la '
                        'evaluación de riesgos a su personal. (periodicidad: al inicio del '
                        'contrato y que tenga vigencia durante la duración del contrato)'),
                    (   '5.3-3',
                        'Actualización de la evaluación de riesgos cada persona que tenga acceso '
                        'físico o lógico a activos o ciberactivos críticos. (periodicidad: cada '
                        '24 meses)')]),
            (   '5.4',
                'Programa de conciencia y entrenamiento en ciberseguridad',
                'Evidencia de ejecución del programa de conciencia y entrenamiento en '
                'ciberseguridad según el rol desempeñado y su criticidad. Periodicidad: cada 24 '
                'meses. Aplica también a los agentes generadores con plantas menores.',
                [   (   '5.4-1',
                        'Evidencia de ejecución del programa de conciencia y entrenamiento en '
                        'ciberseguridad según el rol desempeñado y su criticidad. (periodicidad: '
                        'cada 24 meses)')]),
            (   '5.5',
                'Administración de accesos',
                'Documento procedimiento para gestión de accesos lógicos y físicos. '
                'Periodicidad: cada 24 meses.',
                [   (   '5.5-1',
                        'Documento procedimiento para gestión de accesos lógicos y físicos. '
                        '(periodicidad: cada 24 meses)')]),
            (   '5.6',
                'Verificación de registros de autorización',
                'Evidencias documentales de la verificación periódica. Periodicidad: cada 6 '
                'meses.',
                [   (   '5.6-1',
                        'Evidencias documentales de la verificación periódica. (periodicidad: '
                        'cada 6 meses)')]),
            (   '5.7',
                'Verificación de cuentas y privilegios de acceso',
                'Evidencias documentales de la verificación periódica. Periodicidad: cada 12 '
                'meses.',
                [   (   '5.7-1',
                        'Evidencias documentales de la verificación periódica. (periodicidad: '
                        'cada 12 meses)')]),
            (   '5.8',
                'Procedimiento de revocación de accesos',
                'Evidencia esperada: Documento evidencia registros de revocación de accesos. '
                '(cada 24 meses); Bloqueo (terminación laboral). (cada vez que suceda y máximo '
                '24 horas); Revocación (eliminar o inhabilitar). (cada vez que suceda y máximo '
                '30 días); Cambio de contraseñas (terminación laboral). (cada vez que suceda y '
                'máximo 30 días).',
                [   (   '5.8-1',
                        'Documento evidencia registros de revocación de accesos. (periodicidad: '
                        'cada 24 meses)'),
                    (   '5.8-2',
                        'Bloqueo (terminación laboral). (periodicidad: cada vez que suceda y '
                        'máximo 24 horas)'),
                    (   '5.8-3',
                        'Revocación (eliminar o inhabilitar). (periodicidad: cada vez que suceda '
                        'y máximo 30 días)'),
                    (   '5.8-4',
                        'Cambio de contraseñas (terminación laboral). (periodicidad: cada vez '
                        'que suceda y máximo 30 días)')])]),
    (   '6',
        'Perímetro',
        [   (   '6.1',
                'Perímetros de seguridad lógica',
                'Documento con los perímetros de seguridad lógica y requisitos de accesos. '
                'Periodicidad: cada vez que se actualice. Aplica también a los agentes '
                'generadores con plantas menores.',
                [   (   '6.1-1',
                        'Documento con los perímetros de seguridad lógica y requisitos de '
                        'accesos. (periodicidad: cada vez que se actualice)')]),
            (   '6.2',
                'Listas de acceso',
                'Evidencia esperada: Lista del personal con acceso físico no escoltado o acceso '
                'lógico a los ciberactivos críticos. (cada 6 meses); Evidencia documental de los '
                'cambios realizados. (7 días).',
                [   (   '6.2-1',
                        'Lista del personal con acceso físico no escoltado o acceso lógico a los '
                        'ciberactivos críticos. (periodicidad: cada 6 meses)'),
                    (   '6.2-2',
                        'Evidencia documental de los cambios realizados. (periodicidad: 7 '
                        'días)')]),
            (   '6.3',
                'Procedimiento de monitoreo y registro de acceso',
                'Documento procedimiento para el monitoreo y registro de accesos lógicos a los '
                'perímetros de seguridad físicos y lógicos. Periodicidad: permanente (24/7).',
                [   (   '6.3-1',
                        'Documento procedimiento para el monitoreo y registro de accesos lógicos '
                        'a los perímetros de seguridad físicos y lógicos. (periodicidad: '
                        'permanente (24/7))')]),
            (   '6.4',
                'Validación de cambios',
                'Evidencia esperada: Documento procedimiento de control de cambios. (cada 24 '
                'meses); Evidencia documental de los cambios realizados. (cada vez que se '
                'realice).',
                [   (   '6.4-1',
                        'Documento procedimiento de control de cambios. (periodicidad: cada 24 '
                        'meses)'),
                    (   '6.4-2',
                        'Evidencia documental de los cambios realizados. (periodicidad: cada vez '
                        'que se realice)')]),
            (   '6.5',
                'Procedimiento para habilitar los puntos de acceso',
                'Documento de línea base para equipos de punto de acceso al perímetro de '
                'seguridad lógica. Periodicidad: cada 24 meses.',
                [   (   '6.5-1',
                        'Documento de línea base para equipos de punto de acceso al perímetro de '
                        'seguridad lógica. (periodicidad: cada 24 meses)')]),
            (   '6.6',
                'Procedimiento para la administración de conexiones temporales',
                'Documento procedimiento de administración de conexiones temporales. '
                'Periodicidad: cada 24 meses.',
                [   (   '6.6-1',
                        'Documento procedimiento de administración de conexiones temporales. '
                        '(periodicidad: cada 24 meses)')]),
            (   '6.7',
                'Sistema de control intermedio',
                'Evidencia esperada: Incluirlo en el Documento de inventario. (cada 24 meses); '
                'Evidencia de la revisión periódica del control implementado. (cada vez que se '
                'realice).',
                [   (   '6.7-1',
                        'Incluirlo en el Documento de inventario. (periodicidad: cada 24 meses)'),
                    (   '6.7-2',
                        'Evidencia de la revisión periódica del control implementado. '
                        '(periodicidad: cada vez que se realice)')])]),
    (   '7',
        'Gestión de la seguridad de ciberactivos críticos',
        [   (   '7.1',
                'Procedimiento de control de cambios y gestión de configuraciones',
                'Evidencia esperada: Documento procedimiento gestión de cambios y gestión de '
                'configuración. (cada 24 meses); Evidencias con los cambios realizados. (cada '
                'vez que se realice).',
                [   (   '7.1-1',
                        'Documento procedimiento gestión de cambios y gestión de configuración. '
                        '(periodicidad: cada 24 meses)'),
                    (   '7.1-2',
                        'Evidencias con los cambios realizados. (periodicidad: cada vez que se '
                        'realice)')]),
            (   '7.2',
                'Herramientas de prevención de malware',
                'Evidencia de implementación de herramientas de prevención de software malicioso '
                'o del control compensatorio cuando aplique. Periodicidad: cada vez que se '
                'realice.',
                [   (   '7.2-1',
                        'Evidencia de implementación de herramientas de prevención de software '
                        'malicioso o del control compensatorio cuando aplique. (periodicidad: '
                        'cada vez que se realice)')]),
            (   '7.3',
                'Procedimiento de evaluación de vulnerabilidades',
                'Evidencia esperada: Documento procedimiento de evaluación de vulnerabilidades '
                'técnicas. (cada 24 meses); Evidencia de evaluación periódica de '
                'vulnerabilidades técnicas. (cada vez que se realice); Evidencia de '
                'vulnerabilidades técnicas sobre nuevos ciberactivos. (cada vez que se realice); '
                'Plan de remediación del resultado de análisis de vulnerabilidad técnica. (cada '
                '24 meses). Aplica también a los agentes generadores con plantas menores.',
                [   (   '7.3-1',
                        'Documento procedimiento de evaluación de vulnerabilidades técnicas. '
                        '(periodicidad: cada 24 meses)'),
                    (   '7.3-2',
                        'Evidencia de evaluación periódica de vulnerabilidades técnicas. '
                        '(periodicidad: cada vez que se realice)'),
                    (   '7.3-3',
                        'Evidencia de vulnerabilidades técnicas sobre nuevos ciberactivos. '
                        '(periodicidad: cada vez que se realice)'),
                    (   '7.3-4',
                        'Plan de remediación del resultado de análisis de vulnerabilidad '
                        'técnica. (periodicidad: cada 24 meses)')]),
            (   '7.4',
                'Procedimiento de control ciberactivos críticos transitorios y medios extraíbles',
                'Evidencia esperada: Documento procedimiento control transitorio y medios '
                'extraíbles. (cada 24 meses); Evidencias de control periódico. (cada vez que se '
                'realice). Aplica también a los agentes generadores con plantas menores.',
                [   (   '7.4-1',
                        'Documento procedimiento control transitorio y medios extraíbles. '
                        '(periodicidad: cada 24 meses)'),
                    (   '7.4-2',
                        'Evidencias de control periódico. (periodicidad: cada vez que se '
                        'realice)')]),
            (   '7.5',
                'Procedimiento de actualizaciones y parches de seguridad',
                'Evidencia esperada: Documento procedimiento de actualización e implementación '
                'de parches. (cada 24 meses); Evidencias de los ciclos de parchado. (cada vez '
                'que se realice).',
                [   (   '7.5-1',
                        'Documento procedimiento de actualización e implementación de parches. '
                        '(periodicidad: cada 24 meses)'),
                    (   '7.5-2',
                        'Evidencias de los ciclos de parchado. (periodicidad: cada vez que se '
                        'realice)')]),
            (   '7.6',
                'Procedimiento para identificar y monitorear eventos',
                'Evidencia esperada: Documento procedimiento de monitoreo. (cada 24 meses); '
                'Evidencia de controles implementados. (cada vez que se realice).',
                [   (   '7.6-1',
                        'Documento procedimiento de monitoreo. (periodicidad: cada 24 meses)'),
                    (   '7.6-2',
                        'Evidencia de controles implementados. (periodicidad: cada vez que se '
                        'realice)')])]),
    (   '8',
        'Plan de recuperación de ciberactivos críticos',
        [   (   '8.1',
                'Plan de recuperación y resiliencia',
                'Documento plan de recuperación y resiliencia y los procedimientos asociados. '
                'Periodicidad: cada 12 meses. Aplica también a los agentes generadores con '
                'plantas menores.',
                [   (   '8.1-1',
                        'Documento plan de recuperación y resiliencia y los procedimientos '
                        'asociados. (periodicidad: cada 12 meses)')]),
            (   '8.2',
                'Ejecución y documentación de pruebas o simulacros',
                'Evidencia de pruebas o simulacros, y acciones de mejora de estos. Periodicidad: '
                'cada 12 meses.',
                [   (   '8.2-1',
                        'Evidencia de pruebas o simulacros, y acciones de mejora de estos. '
                        '(periodicidad: cada 12 meses)')]),
            (   '8.3',
                'Registro de cambios del procedimiento de recuperación y resiliencia',
                'Evidencia de los cambios realizados a los procedimientos. Periodicidad: cada 3 '
                'meses.',
                [   (   '8.3-1',
                        'Evidencia de los cambios realizados a los procedimientos. '
                        '(periodicidad: cada 3 meses)')]),
            (   '8.4',
                'Respaldos y almacenamiento de información',
                'Evidencia documentada de los respaldos realizados y almacenamiento de la '
                'información. Periodicidad: cada vez que se realice.',
                [   (   '8.4-1',
                        'Evidencia documentada de los respaldos realizados y almacenamiento de '
                        'la información. (periodicidad: cada vez que se realice)')]),
            (   '8.5',
                'Pruebas a los respaldos y mecanismos de contingencia y continuidad',
                'Evidencia documentada de que se realizan pruebas de respaldo y su resultado. '
                'Periodicidad: cada vez que se realice.',
                [   (   '8.5-1',
                        'Evidencia documentada de que se realizan pruebas de respaldo y su '
                        'resultado. (periodicidad: cada vez que se realice)')])]),
    (   '9',
        'Plan de respuesta ante incidentes en ciberactivos críticos',
        [   (   '9.1',
                'Plan de respuesta a incidentes',
                'Documento con el plan de respuesta ante incidentes. Periodicidad: cada 12 '
                'meses. Aplica también a los agentes generadores con plantas menores.',
                [   (   '9.1-1',
                        'Documento con el plan de respuesta ante incidentes. (periodicidad: cada '
                        '12 meses)')]),
            (   '9.2',
                'Simulacros o pruebas a los planes de respuesta a incientes de ciberseguridad',
                'Evidencia de pruebas o simulacros, y acciones de mejora de estos. Periodicidad: '
                'cada 12 meses.',
                [   (   '9.2-1',
                        'Evidencia de pruebas o simulacros, y acciones de mejora de estos. '
                        '(periodicidad: cada 12 meses)')]),
            (   '9.3',
                'Mantenimientos de los planes de respuesta a incidentes de ciberseguridad',
                'Evidencia del mantenimiento del plan de respuesta de incidentes. Periodicidad: '
                'cada vez que se actualice y máximo 3 meses después de la actualización.',
                [   (   '9.3-1',
                        'Evidencia del mantenimiento del plan de respuesta de incidentes. '
                        '(periodicidad: cada vez que se actualice y máximo 3 meses después de la '
                        'actualización)')])]),
    (   '10',
        'Seguridad física de ciberactivos críticos',
        [   (   '10.1',
                'Plan de seguridad física',
                'Documento plan de seguridad física cumpliendo los requisitos. Periodicidad: '
                'cada 24 meses. Aplica también a los agentes generadores con plantas menores.',
                [   (   '10.1-1',
                        'Documento plan de seguridad física cumpliendo los requisitos. '
                        '(periodicidad: cada 24 meses)')]),
            (   '10.2',
                'Restricción de acceso físico',
                'Evidencia esperada: Evidencia de los controles implementados para protección '
                'física del cableado y otros componentes de comunicación. (cada vez que se '
                'realice); Alarma o alerta en respuesta a fallas de comunicación detectadas. '
                '(cuando se requiera).',
                [   (   '10.2-1',
                        'Evidencia de los controles implementados para protección física del '
                        'cableado y otros componentes de comunicación. (periodicidad: cada vez '
                        'que se realice)'),
                    (   '10.2-2',
                        'Alarma o alerta en respuesta a fallas de comunicación detectadas. '
                        '(periodicidad: cuando se requiera)')]),
            (   '10.3',
                'Procedimiento de control de visitantes',
                'Procedimiento documentado control de visitantes. Periodicidad: cada 24 meses.',
                [   (   '10.3-1',
                        'Procedimiento documentado control de visitantes. (periodicidad: cada 24 '
                        'meses)')]),
            (   '10.4',
                'Procedimiento de mantenimiento y pruebas',
                'Evidencia esperada: Procedimiento documentado de mantenimiento y pruebas '
                'periódicas a los sistemas de control relacionados a la seguridad física. (cada '
                '24 meses); Evidencia mantenimiento y pruebas periódicas. (cada vez que se '
                'realice).',
                [   (   '10.4-1',
                        'Procedimiento documentado de mantenimiento y pruebas periódicas a los '
                        'sistemas de control relacionados a la seguridad física. (periodicidad: '
                        'cada 24 meses)'),
                    (   '10.4-2',
                        'Evidencia mantenimiento y pruebas periódicas. (periodicidad: cada vez '
                        'que se realice)')])]),
    (   '11',
        'Gestión de la cadena de suministro',
        [   (   '11.1',
                'Plan de Gestión de riesgo de la cadena de suministro',
                'Documento y evidencia de la gestión de riesgos de la cadena de suministro que '
                'incluya los riesgos identificados y plan de tratamiento de riesgos. '
                'Periodicidad: cada 24 meses.',
                [   (   '11.1-1',
                        'Documento y evidencia de la gestión de riesgos de la cadena de '
                        'suministro que incluya los riesgos identificados y plan de tratamiento '
                        'de riesgos. (periodicidad: cada 24 meses)')]),
            (   '11.2',
                'Plan de conciencia y entrenamiento en ciberseguridad de la cadena de suministro',
                'Plan de Conciencia y entrenamiento en ciberseguridad de proveedores y '
                'contratistas de la cadena de suministro. Periodicidad: cada 12 meses.',
                [   (   '11.2-1',
                        'Plan de Conciencia y entrenamiento en ciberseguridad de proveedores y '
                        'contratistas de la cadena de suministro. (periodicidad: cada 12 '
                        'meses)')])]),
    (   '12',
        'Gestión de riesgos de ciberseguridad en activos críticos',
        [   (   '12.1',
                'Evaluación de riesgos',
                'Documento con mapa de riesgos. Periodicidad: cada 12 meses. Aplica también a '
                'los agentes generadores con plantas menores.',
                [('12.1-1', 'Documento con mapa de riesgos. (periodicidad: cada 12 meses)')]),
            (   '12.2',
                'Plan de tratamiento de riesgos',
                'Plan de tratamiento de riesgos con medidas de mitigación, plan de '
                'implementación de medidas y asignación de responsabilidades. Periodicidad: cada '
                '12 meses.',
                [   (   '12.2-1',
                        'Plan de tratamiento de riesgos con medidas de mitigación, plan de '
                        'implementación de medidas y asignación de responsabilidades. '
                        '(periodicidad: cada 12 meses)')]),
            (   '12.3',
                'Monitoreo y revisión',
                'Evidencia del monitoreo y registro del plan de tratamiento de riesgos. '
                'Periodicidad: cada 12 meses.',
                [   (   '12.3-1',
                        'Evidencia del monitoreo y registro del plan de tratamiento de riesgos. '
                        '(periodicidad: cada 12 meses)')])])]


def seed_cno1960(db: Session) -> Framework:
    """Idempotent seed: safe to call on every startup/migración.

    Mismo patrón que ``seed_iso27001`` — inserta lo que falte y actualiza
    nombre/guía de evidencia de lo ya existente, más los ``Requirement`` de
    cada control (aquí sí, por no ser texto licenciado).
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

        for control_order, (control_code, control_name, evidence_guidance, requirements) in enumerate(controls):
            control = (
                db.query(Control)
                .filter_by(domain_id=domain.id, code=control_code)
                .one_or_none()
            )
            if control is None:
                control = Control(
                    domain_id=domain.id,
                    code=control_code,
                    name=control_name,
                    evidence_guidance=evidence_guidance,
                    order_index=control_order,
                )
                db.add(control)
                db.flush()
            else:
                control.name = control_name
                control.evidence_guidance = evidence_guidance
                control.order_index = control_order

            for req_order, (req_code, req_text) in enumerate(requirements):
                existing_req = (
                    db.query(Requirement)
                    .filter_by(control_id=control.id, code=req_code)
                    .one_or_none()
                )
                if existing_req is None:
                    db.add(
                        Requirement(
                            control_id=control.id,
                            code=req_code,
                            text=req_text,
                            order_index=req_order,
                        )
                    )
                else:
                    existing_req.text = req_text
                    existing_req.order_index = req_order

    db.commit()
    return framework
