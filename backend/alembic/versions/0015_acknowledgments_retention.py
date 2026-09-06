"""Fase 5 — acuse de recibo (leído y entendido) + retención/disposición.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
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
    # --- Retención / disposición final en Document ---
    disposition_action = postgresql.ENUM(
        "archive", "destroy", name="document_disposition_action", create_type=True
    )
    disposition_action.create(op.get_bind())
    op.add_column(
        "documents",
        sa.Column("legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("documents", sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("disposed_by", sa.String(255), nullable=True))
    op.add_column(
        "documents",
        sa.Column("disposition_action", disposition_action, nullable=True),
    )
    op.add_column("documents", sa.Column("disposition_notes", sa.Text(), nullable=True))

    # --- Acuse de recibo ---
    op.create_table(
        "document_acknowledgments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assigned_by", sa.String(255), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("version_id", "user_id", name="uq_document_ack_version_user"),
    )
    op.create_index(
        "ix_document_acknowledgments_tenant_id", "document_acknowledgments", ["tenant_id"]
    )
    op.create_index(
        "ix_document_acknowledgments_user_id", "document_acknowledgments", ["user_id"]
    )
    _add_rls("document_acknowledgments")


def downgrade() -> None:
    op.drop_table("document_acknowledgments")
    op.drop_column("documents", "disposition_notes")
    op.drop_column("documents", "disposition_action")
    op.drop_column("documents", "disposed_by")
    op.drop_column("documents", "disposed_at")
    op.drop_column("documents", "legal_hold")
    op.execute("DROP TYPE document_disposition_action")
