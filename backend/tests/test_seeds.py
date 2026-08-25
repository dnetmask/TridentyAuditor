"""Fase Q: idempotencia explícita de los 4 seeds.

El lifespan ya los corre en cada arranque, así que la idempotencia se
ejercita implícitamente en toda la suite — pero sin un assert de conteos,
una regresión que duplicara filas pasaría desapercibida hasta producción.
"""

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.frameworks.models import Control, Domain, Framework, Requirement
from app.frameworks.seeds.cno1960 import seed_cno1960
from app.frameworks.seeds.iso27001_2022 import seed_iso27001
from app.wizard.models import WizardPhase, WizardTaskTemplate
from app.wizard.seeds.cno_route import seed_cno_route
from app.wizard.seeds.methodology import seed_wizard_phases


def _counts(db) -> dict[str, int]:
    return {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in (Framework, Domain, Control, Requirement, WizardPhase, WizardTaskTemplate)
    }


def test_seeds_are_idempotent(client):  # client fuerza el lifespan (primera siembra)
    with SessionLocal() as db:
        before = _counts(db)
        seed_iso27001(db)
        seed_cno1960(db)
        seed_wizard_phases(db)
        seed_cno_route(db)
        after = _counts(db)

    assert before == after, f"la re-siembra cambió los conteos: {before} -> {after}"
    # Números de referencia de las dos normas cargadas.
    assert after["frameworks"] == 2
    assert after["domains"] == 4 + 10
    assert after["controls"] == 93 + 41
    assert after["requirements"] == 58  # solo CNO-1960 carga requisitos
    assert after["wizard_phases"] == 8 + 10
