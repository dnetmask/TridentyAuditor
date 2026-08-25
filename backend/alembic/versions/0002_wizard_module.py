"""MOD·WZD — fases/checklist globales + tareas por tenant con RLS.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "wizard_phases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("number", sa.Integer(), nullable=False, unique=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("objective", sa.String(255), nullable=False),
    )

    op.create_table(
        "wizard_task_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "phase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wizard_phases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
    )

    # create_type=True (default) makes create_table below emit CREATE TYPE
    # itself — creating it twice raises DuplicateObject (see 0001).
    wizard_task_status = postgresql.ENUM("pending", "done", name="wizard_task_status")

    op.create_table(
        "tenant_wizard_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "phase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wizard_phases.id"), nullable=False
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wizard_task_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", wizard_task_status, nullable=False, server_default="pending"),
        sa.Column(
            "evidence_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "template_id", name="uq_tenant_wizard_task_template"),
    )
    op.create_index("ix_tenant_wizard_tasks_tenant_id", "tenant_wizard_tasks", ["tenant_id"])

    op.execute("ALTER TABLE tenant_wizard_tasks ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tenant_wizard_tasks FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_tenant_wizard_tasks ON tenant_wizard_tasks
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.drop_table("tenant_wizard_tasks")
    op.execute("DROP TYPE wizard_task_status")
    op.drop_table("wizard_task_templates")
    op.drop_table("wizard_phases")
