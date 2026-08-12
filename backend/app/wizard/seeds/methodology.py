"""Seed de las 8 fases del asistente paso a paso (MOD·WZD).

Checklist de referencia por fase — práctica estándar de implementación de un
SGSI ISO/IEC 27001, no texto normativo del estándar. Cada tenant instancia
su propia copia editable de estas tareas vía ``service.instantiate`` al
arrancar el ciclo (ver sección 02 del documento de arquitectura).
"""

from sqlalchemy.orm import Session

from app.wizard.models import WizardPhase, WizardTaskTemplate

# (number, code, name, objective, [(title, description, requires_evidence), ...])
PHASES: list[tuple[int, str, str, str, list[tuple[str, str | None, bool]]]] = [
    (
        1,
        "diagnostico",
        "Diagnóstico inicial",
        "Brechas vs Anexo A",
        [
            ("Diagnóstico de brechas contra los 93 controles del Anexo A", None, True),
            ("Evaluar el nivel de madurez actual del SGSI", None, False),
            ("Elaborar plan de acción de alto nivel a partir del diagnóstico", None, True),
        ],
    ),
    (
        2,
        "contexto",
        "Contexto y alcance",
        "Límites del SGSI",
        [
            ("Documentar el contexto de la organización y sus partes interesadas", None, True),
            ("Definir y documentar el alcance del SGSI", None, True),
            ("Identificar requisitos legales, regulatorios y contractuales aplicables", None, True),
        ],
    ),
    (
        3,
        "liderazgo",
        "Liderazgo y política",
        "Compromiso directivo",
        [
            ("Redactar y aprobar la Política de Seguridad de la Información", None, True),
            ("Definir roles, responsabilidades y autoridades del SGSI", None, True),
            ("Obtener acta de compromiso de la alta dirección", None, True),
        ],
    ),
    (
        4,
        "riesgos",
        "Riesgos y tratamiento",
        "Matriz y plan",
        [
            ("Definir la metodología de valoración de riesgos", None, True),
            ("Elaborar el inventario de activos de información", None, True),
            ("Realizar la valoración de riesgos y construir la matriz", None, True),
            ("Elaborar el plan de tratamiento de riesgos", None, True),
        ],
    ),
    (
        5,
        "soa",
        "SoA y controles",
        "93 controles Anexo A",
        [
            ("Elaborar la Declaración de Aplicabilidad (SoA)", None, True),
            ("Asignar dueño por cada control aplicable", None, False),
            ("Documentar la justificación de exclusión de controles no aplicables", None, True),
        ],
    ),
    (
        6,
        "implementacion",
        "Implementación",
        "Con evidencia real",
        [
            ("Implementar los controles priorizados del plan de tratamiento", None, True),
            ("Publicar y socializar las políticas y procedimientos del SGSI", None, True),
            ("Ejecutar la campaña inicial de concientización", None, True),
        ],
    ),
    (
        7,
        "auditoria_interna",
        "Auditoría interna",
        "Hallazgos y CAPA",
        [
            ("Elaborar el programa anual de auditoría interna", None, True),
            ("Ejecutar la auditoría interna sobre todos los dominios", None, True),
            ("Registrar hallazgos y no conformidades", None, True),
            ("Definir y dar seguimiento a las acciones correctivas (CAPA)", None, True),
        ],
    ),
    (
        8,
        "revision_certificacion",
        "Revisión y certificación",
        "Con auditor externo",
        [
            ("Realizar la revisión por la dirección", None, True),
            ("Consolidar el expediente de auditoría para el auditor externo", None, True),
            ("Ejecutar la auditoría de certificación (etapa 1 y 2)", "Gestionada por el ente certificador", False),
        ],
    ),
]


def seed_wizard_phases(db: Session) -> None:
    """Idempotent seed: safe to call on every startup/migration."""
    for number, code, name, objective, tasks in PHASES:
        phase = db.query(WizardPhase).filter_by(number=number).one_or_none()
        if phase is None:
            phase = WizardPhase(number=number, code=code, name=name, objective=objective)
            db.add(phase)
            db.flush()

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

    db.commit()
