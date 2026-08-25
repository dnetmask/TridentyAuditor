"""Seed de las 10 fases de la Ruta CNO (MOD·WZD) — solo para tenants CNO-1960.

Un tenant CNO-1960 no es un proyecto de implementación desde cero como un
SGSI ISO 27001 (ver ``methodology.py``): es una obligación regulatoria ya
vigente, con controles de cumplimiento periódico (cada 3, 6, 12 o 24 meses,
o "cada vez que se requiera"). Por eso la Ruta CNO no repite los 41 controles
uno a uno — eso ya está en MOD·SOA/Marco normativo con su propia guía de
evidencia y seguimiento de aplicabilidad — sino que agrupa la primera puesta
en marcha de cada numeral en 2-4 tareas de alto nivel, nombrando el o los
entregables más relevantes de ese numeral y remitiendo a MOD·SOA para el
resto del detalle. Cada fase corresponde 1 a 1 con un numeral/dominio del
Anexo 1 del Acuerdo 1960 (mismo orden que ``app/frameworks/seeds/cno1960.py``),
para que "Fase N" en la Ruta CNO y el numeral que cita en su nombre apunten
siempre al mismo lugar en Marco normativo.
"""

from sqlalchemy.orm import Session

from app.frameworks.models import Framework
from app.wizard.models import WizardPhase, WizardTaskTemplate

FRAMEWORK_CODE = "CNO-1960"

# (number, code, name, objective, [(title, description, requires_evidence), ...])
PHASES: list[tuple[int, str, str, str, list[tuple[str, str | None, bool]]]] = [
    (
        1,
        "cumplimiento",
        "Cumplimiento y auditoría",
        "Programa de auditoría (numeral 3)",
        [
            (
                "Definir el programa de auditorías internas de ciberseguridad exigido por el Acuerdo 1960",
                "Reporte de auditorías internas con periodicidad de 24 meses (control 3.1) — aplica "
                "también a los agentes generadores con plantas menores.",
                True,
            ),
        ],
    ),
    (
        2,
        "activos_criticos",
        "Identificación de activos críticos",
        "Inventario de ciberactivos (numeral 4)",
        [
            (
                "Elaborar y hacer aprobar por la entidad el inventario de activos y ciberactivos críticos",
                "Lista de activos/ciberactivos críticos con aprobación formal, revisada cada 12 meses "
                "(control 4.1). Para plantas menores equivale al inventario de ciberactivos.",
                True,
            ),
            (
                "Construir el inventario detallado de ciberactivos críticos a partir de los activos críticos",
                "Inventario con información que identifique de forma única cada ciberactivo en la red y "
                "el activo crítico al que pertenece (control 4.2), actualizado junto con la revisión "
                "del 4.1.",
                True,
            ),
        ],
    ),
    (
        3,
        "gobierno_personal",
        "Gobierno y gestión del personal",
        "Política, roles y accesos (numeral 5)",
        [
            (
                "Redactar y aprobar la política o lineamiento de ciberseguridad",
                "Documento de política/lineamiento, a actualizar cada vez que se requiera (control 5.1).",
                True,
            ),
            (
                "Designar y notificar al CNO el responsable de ciberseguridad",
                "Documento de asignación o delegación enviado al CNO, a actualizar dentro de los 20 "
                "días calendario siguientes a cualquier cambio (control 5.2).",
                True,
            ),
            (
                "Poner en marcha la evaluación de riesgos y los procedimientos de acceso del personal",
                "Cubre la evaluación de riesgos al personal/proveedores (5.3), la administración de "
                "accesos (5.5), la verificación periódica de cuentas y privilegios (5.6-5.7) y la "
                "revocación de accesos (5.8) — ver el detalle de cada control en MOD·SOA.",
                True,
            ),
            (
                "Ejecutar el programa de conciencia y entrenamiento en ciberseguridad",
                "Evidencia de ejecución según el rol desempeñado y su criticidad, con periodicidad de "
                "24 meses (control 5.4).",
                True,
            ),
        ],
    ),
    (
        4,
        "perimetro",
        "Perímetro",
        "Perímetros de seguridad (numeral 6)",
        [
            (
                "Documentar los perímetros de seguridad lógica y sus requisitos de acceso",
                "Documento de perímetros y requisitos de acceso, a actualizar cada vez que se modifique "
                "(control 6.1).",
                True,
            ),
            (
                "Implementar el monitoreo permanente de accesos y el control de listas de acceso",
                "Cubre el procedimiento de monitoreo y registro de accesos 24/7 (control 6.3) y las "
                "listas de acceso físico/lógico revisadas cada 6 meses (control 6.2).",
                True,
            ),
            (
                "Establecer los procedimientos de control de cambios, puntos de acceso y conexiones temporales",
                "Cubre la validación de cambios (6.4), la habilitación de puntos de acceso (6.5), las "
                "conexiones temporales (6.6) y el sistema de control intermedio (6.7) — ver el detalle "
                "de cada control en MOD·SOA.",
                True,
            ),
        ],
    ),
    (
        5,
        "gestion_seguridad",
        "Gestión de la seguridad de ciberactivos críticos",
        "Cambios, malware y vulnerabilidades (numeral 7)",
        [
            (
                "Documentar el procedimiento de control de cambios y gestión de configuraciones",
                "Procedimiento a revisar cada 24 meses, con evidencia de cada cambio realizado "
                "(control 7.1).",
                True,
            ),
            (
                "Implementar las herramientas de prevención de malware y el ciclo de parches",
                "Cubre la prevención de software malicioso o su control compensatorio (7.2) y el "
                "procedimiento de actualizaciones/parches de seguridad (7.5).",
                True,
            ),
            (
                "Poner en marcha la evaluación periódica de vulnerabilidades y su plan de remediación",
                "Procedimiento de evaluación de vulnerabilidades técnicas con plan de remediación cada "
                "24 meses (control 7.3), incluida la evaluación sobre ciberactivos nuevos.",
                True,
            ),
            (
                "Establecer el control de ciberactivos transitorios/medios extraíbles y el monitoreo de eventos",
                "Cubre el procedimiento de control de ciberactivos transitorios y medios extraíbles "
                "(7.4) y el procedimiento de monitoreo de eventos (7.6).",
                True,
            ),
        ],
    ),
    (
        6,
        "recuperacion",
        "Plan de recuperación de ciberactivos críticos",
        "Plan de recuperación y respaldos (numeral 8)",
        [
            (
                "Elaborar el plan de recuperación y resiliencia con sus procedimientos asociados",
                "Documento a revisar cada 12 meses (control 8.1).",
                True,
            ),
            (
                "Ejecutar y documentar pruebas o simulacros de recuperación",
                "Evidencia de pruebas/simulacros y acciones de mejora cada 12 meses (control 8.2); "
                "registrar los cambios al procedimiento cada 3 meses (control 8.3).",
                True,
            ),
            (
                "Poner en marcha los respaldos de información y sus pruebas periódicas",
                "Evidencia de los respaldos y su almacenamiento (control 8.4) y de las pruebas a esos "
                "respaldos y a los mecanismos de contingencia y continuidad (control 8.5), cada vez "
                "que se realicen.",
                True,
            ),
        ],
    ),
    (
        7,
        "respuesta_incidentes",
        "Plan de respuesta ante incidentes en ciberactivos críticos",
        "Plan de respuesta a incidentes (numeral 9)",
        [
            (
                "Elaborar el plan de respuesta ante incidentes de ciberseguridad",
                "Documento a revisar cada 12 meses (control 9.1).",
                True,
            ),
            (
                "Ejecutar simulacros del plan de respuesta y mantenerlo actualizado",
                "Evidencia de simulacros cada 12 meses (control 9.2) y evidencia de mantenimiento cada "
                "vez que se actualice, máximo 3 meses después (control 9.3).",
                True,
            ),
        ],
    ),
    (
        8,
        "seguridad_fisica",
        "Seguridad física de ciberactivos críticos",
        "Plan de seguridad física (numeral 10)",
        [
            (
                "Elaborar el plan de seguridad física de los ciberactivos críticos",
                "Documento a revisar cada 24 meses (control 10.1).",
                True,
            ),
            (
                "Implementar la restricción de acceso físico y el control de visitantes",
                "Cubre la protección física del cableado y otros componentes de comunicación (10.2) y "
                "el procedimiento de control de visitantes (10.3), cada 24 meses.",
                True,
            ),
            (
                "Establecer el mantenimiento y las pruebas periódicas de los sistemas de seguridad física",
                "Procedimiento y evidencia de mantenimiento/pruebas periódicas cada 24 meses "
                "(control 10.4).",
                True,
            ),
        ],
    ),
    (
        9,
        "cadena_suministro",
        "Gestión de la cadena de suministro",
        "Riesgo de proveedores (numeral 11)",
        [
            (
                "Elaborar el plan de gestión de riesgo de la cadena de suministro",
                "Documento con los riesgos identificados y el plan de tratamiento, cada 24 meses "
                "(control 11.1).",
                True,
            ),
            (
                "Ejecutar el plan de conciencia y entrenamiento para proveedores y contratistas",
                "Plan de conciencia y entrenamiento en ciberseguridad de la cadena de suministro, cada "
                "12 meses (control 11.2).",
                True,
            ),
        ],
    ),
    (
        10,
        "gestion_riesgos",
        "Gestión de riesgos de ciberseguridad en activos críticos",
        "Mapa y tratamiento de riesgos (numeral 12)",
        [
            (
                "Elaborar el mapa de riesgos de ciberseguridad de los activos críticos",
                "Documento con mapa de riesgos, cada 12 meses (control 12.1) — puede apoyarse en "
                "MOD·RSK.",
                True,
            ),
            (
                "Elaborar el plan de tratamiento de riesgos",
                "Con medidas de mitigación, plan de implementación y responsables asignados, cada 12 "
                "meses (control 12.2).",
                True,
            ),
            (
                "Poner en marcha el monitoreo y la revisión del plan de tratamiento de riesgos",
                "Evidencia del monitoreo y registro del plan de tratamiento de riesgos, cada 12 meses "
                "(control 12.3).",
                True,
            ),
        ],
    ),
]


def seed_cno_route(db: Session) -> None:
    """Idempotent seed: safe to call on every startup/migración.

    Mismo patrón que ``seed_wizard_phases`` — inserta lo que falte y
    actualiza la ``description`` de las tareas ya existentes. Corre después
    de ``seed_cno1960`` (necesita el framework ya sembrado).
    """
    framework = db.query(Framework).filter_by(code=FRAMEWORK_CODE).one()

    for number, code, name, objective, tasks in PHASES:
        phase = (
            db.query(WizardPhase)
            .filter_by(framework_id=framework.id, number=number)
            .one_or_none()
        )
        if phase is None:
            phase = WizardPhase(
                framework_id=framework.id, number=number, code=code, name=name, objective=objective
            )
            db.add(phase)
            db.flush()
        else:
            phase.code = code
            phase.name = name
            phase.objective = objective

        for order_index, (title, description, requires_evidence) in enumerate(tasks):
            existing = (
                db.query(WizardTaskTemplate)
                .filter_by(phase_id=phase.id, title=title)
                .one_or_none()
            )
            if existing is None:
                db.add(
                    WizardTaskTemplate(
                        phase_id=phase.id,
                        title=title,
                        description=description,
                        requires_evidence=requires_evidence,
                        order_index=order_index,
                    )
                )
            else:
                existing.description = description
                existing.order_index = order_index

    db.commit()
