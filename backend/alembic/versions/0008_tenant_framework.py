"""Norma por tenant — Tenant.framework_id (Fase 0: se agrega CNO-1960).

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable primero: un tenant ya existente en una base real necesita
    # quedar asignado a una norma antes de que la columna pueda ser NOT NULL.
    op.add_column(
        "tenants",
        sa.Column(
            "framework_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("frameworks.id"),
            nullable=True,
        ),
    )

    # Backfill: hasta ahora ISO/IEC 27001:2022 era la única norma posible, así
    # que es la única respuesta correcta para todo tenant creado antes de esta
    # migración. Si la base es nueva (sin tenants todavía, o sin el framework
    # sembrado aún porque nunca arrancó la aplicación) este UPDATE no afecta
    # ninguna fila — no hay tenant sin norma que romper.
    op.execute(
        """
        UPDATE tenants
        SET framework_id = (SELECT id FROM frameworks WHERE code = 'ISO27001:2022')
        WHERE framework_id IS NULL
        """
    )

    op.alter_column("tenants", "framework_id", nullable=False)


def downgrade() -> None:
    op.drop_column("tenants", "framework_id")
