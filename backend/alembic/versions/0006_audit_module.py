"""MOD·AUD — programa de auditoría interna y hallazgos con CAPA.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_rls(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_{table_name} ON {table_name}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def upgrade() -> None:
    audit_status = postgresql.ENUM("planned", "in_progress", "completed", name="audit_status")
    finding_classification = postgresql.ENUM(
        "major_nc", "minor_nc", "observation", "improvement", name="finding_classification"
    )
    finding_status = postgresql.ENUM("open", "in_progress", "closed", name="finding_status")

    op.create_table(
        "audit_programs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column(
            "domain_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("domains.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column(
            "auditor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("executed_date", sa.Date(), nullable=True),
        sa.Column("status", audit_status, nullable=False, server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_programs_tenant_id", "audit_programs", ["tenant_id"])
    _add_rls("audit_programs")

    op.create_table(
        "audit_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_programs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("controls.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("classification", finding_classification, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("corrective_action", sa.Text(), nullable=True),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", finding_status, nullable=False, server_default="open"),
        sa.Column(
            "evidence_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_findings_tenant_id", "audit_findings", ["tenant_id"])
    op.create_index("ix_audit_findings_audit_id", "audit_findings", ["audit_id"])
    _add_rls("audit_findings")


def downgrade() -> None:
    op.drop_table("audit_findings")
    op.execute("DROP TYPE finding_status")
    op.execute("DROP TYPE finding_classification")
    op.drop_table("audit_programs")
    op.execute("DROP TYPE audit_status")
