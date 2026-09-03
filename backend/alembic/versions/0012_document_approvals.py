"""Fase 2 — aprobación multinivel: tabla de firmas con sello verificable.

Cada firma (gerente de área, seguridad de la información) es una fila con el
SHA-256 del binario al momento de firmar. Las versiones aprobadas antes de
esta fase conservan su ``approved_by``/``approved_at`` de un solo paso — no
se les inventan firmas retroactivas.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def upgrade() -> None:
    # create_type=False: el tipo se crea explícitamente aquí; sin la bandera,
    # create_table intentaría crearlo de nuevo (DuplicateObject).
    approval_step = postgresql.ENUM(
        "area_manager", "security", name="document_approval_step", create_type=False
    )
    approval_step.create(op.get_bind())
    op.create_table(
        "document_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", approval_step, nullable=False),
        sa.Column("signed_by", sa.String(255), nullable=False),
        sa.Column(
            "signed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("signed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.UniqueConstraint("version_id", "step", name="uq_document_approval_version_step"),
    )
    op.create_index("ix_document_approvals_tenant_id", "document_approvals", ["tenant_id"])
    op.create_index("ix_document_approvals_version_id", "document_approvals", ["version_id"])
    _add_rls("document_approvals")


def downgrade() -> None:
    op.drop_table("document_approvals")
    op.execute("DROP TYPE document_approval_step")
