"""Seed de las 8 fases de la Ruta SGSI (MOD·WZD) — solo para tenants ISO/IEC 27001:2022.

Checklist de referencia por fase — práctica estándar de implementación de un
SGSI ISO/IEC 27001, no texto normativo del estándar. La ``description`` de
cada tarea es una guía de qué evidencia suele demostrar que la tarea está
resuelta (ejemplos, no la única forma válida). Cada tenant instancia su
propia copia editable de estas tareas vía ``service.instantiate`` al
arrancar el ciclo (ver sección 02 del documento de arquitectura).

Un tenant CNO-1960 no ve esta ruta — ve la suya propia, ``cno_route.py``.
"""

from sqlalchemy.orm import Session

from app.frameworks.models import Framework
from app.wizard.models import WizardPhase, WizardTaskTemplate

FRAMEWORK_CODE = "ISO27001:2022"

# (number, code, name, objective, [(title, description, requires_evidence), ...])
PHASES: list[tuple[int, str, str, str, list[tuple[str, str | None, bool]]]] = [
    (
        1,
        "diagnostico",
        "Diagnóstico inicial",
        "Brechas vs Anexo A",
        [
            (
                "Diagnóstico de brechas contra los 93 controles del Anexo A",
                "Informe de diagnóstico (gap analysis) con el estado actual de cada control frente "
                "al esperado y las brechas identificadas.",
                True,
            ),
            (
                "Evaluar el nivel de madurez actual del SGSI",
                "Matriz o informe de madurez (ej. escala 0-5) por dominio de seguridad, con el nivel "
                "actual justificado.",
                False,
            ),
            (
                "Elaborar plan de acción de alto nivel a partir del diagnóstico",
                "Plan de acción con actividades, responsables y fechas, derivado directamente de las "
                "brechas del diagnóstico.",
                True,
            ),
        ],
    ),
    (
        2,
        "contexto",
        "Contexto y alcance",
        "Límites del SGSI",
        [
            (
                "Documentar el contexto de la organización y sus partes interesadas",
                "Documento de contexto organizacional (factores internos/externos relevantes) y "
                "matriz de partes interesadas con sus expectativas.",
                True,
            ),
            (
                "Definir y documentar el alcance del SGSI",
                "Declaración de alcance del SGSI aprobada, indicando procesos, sedes, sistemas y "
                "exclusiones.",
                True,
            ),
            (
                "Identificar requisitos legales, regulatorios y contractuales aplicables",
                "Matriz de requisitos legales/regulatorios/contractuales aplicables con su estado de "
                "cumplimiento.",
                True,
            ),
        ],
    ),
    (
        3,
        "liderazgo",
        "Liderazgo y política",
        "Compromiso directivo",
        [
            (
                "Redactar y aprobar la Política de Seguridad de la Información",
                "Política de seguridad firmada/aprobada por la alta dirección, con fecha y evidencia "
                "de publicación.",
                True,
            ),
            (
                "Definir roles, responsabilidades y autoridades del SGSI",
                "Documento de roles y responsabilidades del SGSI (ej. Comité de Seguridad, CISO) con "
                "nombramientos formales.",
                True,
            ),
            (
                "Obtener acta de compromiso de la alta dirección",
                "Acta de reunión o comunicado firmado por la dirección donde se compromete recursos y "
                "liderazgo al SGSI.",
                True,
            ),
        ],
    ),
    (
        4,
        "riesgos",
        "Riesgos y tratamiento",
        "Matriz y plan",
        [
            (
                "Definir la metodología de valoración de riesgos",
                "Documento de metodología aprobado (escalas de probabilidad/impacto, criterios de "
                "aceptación) — en esta plataforma corresponde a la metodología fija de MOD·RSK.",
                True,
            ),
            (
                "Elaborar el inventario de activos de información",
                "Inventario de activos con dueño y categoría, cargado en MOD·RSK (pestaña Activos).",
                True,
            ),
            (
                "Realizar la valoración de riesgos y construir la matriz",
                "Matriz de riesgos con nivel inherente calculado, cargada en MOD·RSK.",
                True,
            ),
            (
                "Elaborar el plan de tratamiento de riesgos",
                "Plan de tratamiento por riesgo (decisión y acciones) registrado en el detalle de cada "
                "riesgo en MOD·RSK.",
                True,
            ),
        ],
    ),
    (
        5,
        "soa",
        "SoA y controles",
        "93 controles Anexo A",
        [
            (
                "Elaborar la Declaración de Aplicabilidad (SoA)",
                "SoA instanciada en MOD·SOA con aplicabilidad definida para los 93 controles.",
                True,
            ),
            (
                "Asignar dueño por cada control aplicable",
                "Cada control aplicable en MOD·SOA con un dueño asignado, responsable de su "
                "implementación.",
                False,
            ),
            (
                "Documentar la justificación de exclusión de controles no aplicables",
                "Justificación registrada en MOD·SOA para cada control marcado como no aplicable.",
                True,
            ),
        ],
    ),
    (
        6,
        "implementacion",
        "Implementación",
        "Con evidencia real",
        [
            (
                "Implementar los controles priorizados del plan de tratamiento",
                "Evidencia concreta por control implementado — ver la guía de evidencia de cada "
                "control en MOD·SOA/Marco normativo — cargada en MOD·DOC.",
                True,
            ),
            (
                "Publicar y socializar las políticas y procedimientos del SGSI",
                "Registro de publicación (intranet, correo) y evidencia de socialización (acta, "
                "lista de asistencia).",
                True,
            ),
            (
                "Ejecutar la campaña inicial de concientización",
                "Material de la campaña y registro de asistencia/resultados de la evaluación de "
                "concientización.",
                True,
            ),
        ],
    ),
    (
        7,
        "auditoria_interna",
        "Auditoría interna",
        "Hallazgos y CAPA",
        [
            (
                "Elaborar el programa anual de auditoría interna",
                "Programa de auditoría aprobado con alcance, criterios y calendario por dominio/"
                "proceso.",
                True,
            ),
            (
                "Ejecutar la auditoría interna sobre todos los dominios",
                "Informe de auditoría interna con la evidencia revisada por dominio y la conclusión "
                "de conformidad.",
                True,
            ),
            (
                "Registrar hallazgos y no conformidades",
                "Registro de hallazgos/no conformidades con su clasificación (mayor/menor/oportunidad "
                "de mejora).",
                True,
            ),
            (
                "Definir y dar seguimiento a las acciones correctivas (CAPA)",
                "Plan de acciones correctivas con causa raíz, responsable, fecha y evidencia de "
                "cierre.",
                True,
            ),
        ],
    ),
    (
        8,
        "revision_certificacion",
        "Revisión y certificación",
        "Con auditor externo",
        [
            (
                "Realizar la revisión por la dirección",
                "Acta de revisión por la dirección con las entradas y salidas requeridas (resultados "
                "de auditorías, desempeño de riesgos, decisiones).",
                True,
            ),
            (
                "Consolidar el expediente de auditoría para el auditor externo",
                "Expediente consolidado: SoA, matriz de riesgos, políticas aprobadas, resultados de "
                "auditoría interna y CAPA, listo para el auditor externo.",
                True,
            ),
            (
                "Ejecutar la auditoría de certificación (etapa 1 y 2)",
                "Gestionada por el ente certificador — el expediente consolidado en la tarea anterior "
                "es el insumo que se le entrega.",
                False,
            ),
        ],
    ),
]


def seed_wizard_phases(db: Session) -> None:
    """Idempotent seed: safe to call on every startup/migración.

    Inserta lo que falte y también actualiza la ``description`` de las
    tareas ya existentes, para que revisar la guía de evidencia en este
    archivo se refleje en despliegues que ya habían sembrado el checklist.
    Corre después de ``seed_iso27001`` (necesita el framework ya sembrado).
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
