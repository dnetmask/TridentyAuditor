"""COMP — evaluación del auditor (MOD·AUD) + % avance y costo en CAPA.

Respuesta al análisis de competencia (Kawak): su módulo de Auditorías tiene
"Evaluación de auditores" y su CAPA ("Mejoramiento Continuo") trackea % de
avance y costo. Se suma paridad funcional sin salir del núcleo único: dos
columnas en el programa de auditoría y dos en el hallazgo.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Evaluación del auditor líder al cerrar la auditoría (COMP-A) ---
    op.add_column("audit_programs", sa.Column("auditor_score", sa.Integer(), nullable=True))
    op.add_column("audit_programs", sa.Column("auditor_evaluation", sa.Text(), nullable=True))

    # --- % de avance y costo estimado de la acción CAPA (COMP-B) ---
    op.add_column(
        "audit_findings",
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "audit_findings",
        sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audit_findings", "estimated_cost")
    op.drop_column("audit_findings", "progress_pct")
    op.drop_column("audit_programs", "auditor_evaluation")
    op.drop_column("audit_programs", "auditor_score")
