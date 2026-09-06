"""MOD·PRC (Fase 4) — mapa de procesos + enlaces documento↔proceso.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
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
    op.create_table(
        "processes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_process_tenant_name"),
    )
    op.create_index("ix_processes_tenant_id", "processes", ["tenant_id"])
    _add_rls("processes")

    op.create_table(
        "document_process_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "process_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("processes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("process_id", "document_id", name="uq_document_process_link"),
    )
    op.create_index(
        "ix_document_process_links_tenant_id", "document_process_links", ["tenant_id"]
    )
    _add_rls("document_process_links")


def downgrade() -> None:
    op.drop_table("document_process_links")
    op.drop_table("processes")
