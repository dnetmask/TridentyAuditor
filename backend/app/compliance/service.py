"""Indicador de cumplimiento del SGSI — sección 'Estado del proyecto'.

Un solo número, visible en todo momento en la barra superior, que combina
dos señales que ya exigen evidencia real (no solo una casilla marcada):

- MOD·SOA: de los controles aplicables, cuántos tienen un documento de
  evidencia vinculado con al menos una versión APROBADA.
- MOD·WZD: de las tareas del asistente que exigen evidencia, cuántas están
  cerradas (``complete_task`` ya impide cerrarlas sin evidencia aprobada —
  ver app/wizard/service.py — así que "cerrada" implica "evidenciada").

No incluye MOD·RSK (la evidencia de tratamiento de riesgos es una señal
distinta — "¿se aplicó el tratamiento?", no "¿el control está cumplido?")
ni el marco NIST CSF 2.0 (Fase 2, sin cargar todavía).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents.service import approved_document_ids
from app.soa.models import SoaEntry
from app.wizard.models import TenantWizardTask, WizardTaskStatus

SOA_WEIGHT = 0.6
WIZARD_WEIGHT = 0.4


def _percentage(evidenced: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(evidenced * 100 / total, 1)


def _soa_component(db: Session, tenant_id: str) -> dict:
    entries = list(
        db.scalars(
            select(SoaEntry).where(SoaEntry.tenant_id == tenant_id, SoaEntry.is_applicable.is_(True))
        )
    )
    approved_ids = approved_document_ids(db, tenant_id)
    evidenced = sum(1 for e in entries if e.evidence_document_id in approved_ids)
    total = len(entries)
    return {
        "key": "soa",
        "label": "Controles del SoA con evidencia aprobada",
        "evidenced": evidenced,
        "total": total,
        "percentage": _percentage(evidenced, total),
    }


def _wizard_component(db: Session, tenant_id: str) -> dict:
    tasks = list(
        db.scalars(
            select(TenantWizardTask).where(
                TenantWizardTask.tenant_id == tenant_id,
                TenantWizardTask.requires_evidence.is_(True),
            )
        )
    )
    evidenced = sum(1 for t in tasks if t.status == WizardTaskStatus.DONE)
    total = len(tasks)
    return {
        "key": "wizard",
        "label": "Tareas del asistente con evidencia aprobada",
        "evidenced": evidenced,
        "total": total,
        "percentage": _percentage(evidenced, total),
    }


def get_overview(db: Session, tenant_id: str) -> dict:
    soa = _soa_component(db, tenant_id)
    wizard = _wizard_component(db, tenant_id)
    percentage = round(soa["percentage"] * SOA_WEIGHT + wizard["percentage"] * WIZARD_WEIGHT, 1)
    return {"percentage": percentage, "components": [soa, wizard]}
