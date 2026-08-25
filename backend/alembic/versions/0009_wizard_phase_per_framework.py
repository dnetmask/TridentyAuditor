"""WizardPhase.framework_id — cada norma trae su propia ruta paso a paso.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable primero: las 8 fases ya sembradas (todas de la metodología ISO)
    # necesitan quedar asignadas a un framework antes de que la columna
    # pueda ser NOT NULL — mismo patrón que 0008 (Tenant.framework_id).
    op.add_column(
        "wizard_phases",
        sa.Column(
            "framework_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("frameworks.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )

    # Backfill: toda fase sembrada antes de esta migración es de la
    # metodología ISO 27001 (la única que existía). Si la base es nueva (sin
    # fases sembradas todavía) este UPDATE no afecta ninguna fila.
    op.execute(
        """
        UPDATE wizard_phases
        SET framework_id = (SELECT id FROM frameworks WHERE code = 'ISO27001:2022')
        WHERE framework_id IS NULL
        """
    )

    op.alter_column("wizard_phases", "framework_id", nullable=False)

    # number/code eran únicos a nivel global; ahora cada norma trae su propia
    # numeración (Ruta SGSI y Ruta CNO ambas empiezan en la fase 1), así que
    # la unicidad pasa a ser compuesta con framework_id.
    op.drop_constraint("uq_wizard_phases_number", "wizard_phases", type_="unique")
    op.drop_constraint("uq_wizard_phases_code", "wizard_phases", type_="unique")
    op.create_unique_constraint(
        "uq_wizard_phase_framework_number", "wizard_phases", ["framework_id", "number"]
    )
    op.create_unique_constraint(
        "uq_wizard_phase_framework_code", "wizard_phases", ["framework_id", "code"]
    )


def downgrade() -> None:
    # No se restauran los uniques globales de ``number``/``code``: una vez
    # que existe más de una ruta (ISO y CNO ambas numeran sus fases desde 1),
    # esa unicidad global ya no puede sostenerse sin antes decidir qué hacer
    # con los datos — no es una operación de esquema, así que queda fuera de
    # este downgrade (igual que 0008 no intenta reconstruir el estado previo
    # de los tenants, solo retira la columna que agregó).
    op.drop_constraint("uq_wizard_phase_framework_number", "wizard_phases", type_="unique")
    op.drop_constraint("uq_wizard_phase_framework_code", "wizard_phases", type_="unique")
    op.drop_column("wizard_phases", "framework_id")
