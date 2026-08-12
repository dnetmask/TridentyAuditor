"""MOD·SOA y MOD·RSK — tablas de tenant con RLS.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
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
    # --- MOD·SOA ---
    soa_status = postgresql.ENUM("not_started", "in_progress", "implemented", name="soa_implementation_status")

    op.create_table(
        "soa_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("controls.id"), nullable=False),
        sa.Column("is_applicable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("implementation_status", soa_status, nullable=False, server_default="not_started"),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "evidence_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "control_id", name="uq_soa_entry_tenant_control"),
    )
    op.create_index("ix_soa_entries_tenant_id", "soa_entries", ["tenant_id"])
    _add_rls("soa_entries")

    # --- MOD·RSK ---
    asset_category = postgresql.ENUM(
        "information", "software", "hardware", "service", "people", "facility", "other",
        name="asset_category",
    )
    treatment_decision = postgresql.ENUM("mitigate", "accept", "transfer", "avoid", name="treatment_decision")
    risk_level_inherent = postgresql.ENUM("low", "medium", "high", "critical", name="risk_level_inherent")
    risk_level_residual = postgresql.ENUM("low", "medium", "high", "critical", name="risk_level_residual")
    risk_status = postgresql.ENUM("open", "treating", "closed", name="risk_status")

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", asset_category, nullable=False),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_assets_tenant_id", "assets", ["tenant_id"])
    _add_rls("assets")

    op.create_table(
        "risks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("threat", sa.String(255), nullable=True),
        sa.Column("vulnerability", sa.String(255), nullable=True),
        sa.Column("likelihood", sa.Integer(), nullable=False),
        sa.Column("impact", sa.Integer(), nullable=False),
        sa.Column("inherent_score", sa.Integer(), nullable=False),
        sa.Column("inherent_level", risk_level_inherent, nullable=False),
        sa.Column("treatment_decision", treatment_decision, nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("residual_likelihood", sa.Integer(), nullable=True),
        sa.Column("residual_impact", sa.Integer(), nullable=True),
        sa.Column("residual_score", sa.Integer(), nullable=True),
        sa.Column("residual_level", risk_level_residual, nullable=True),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", risk_status, nullable=False, server_default="open"),
        sa.Column(
            "evidence_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_risks_tenant_id", "risks", ["tenant_id"])
    _add_rls("risks")

    op.create_table(
        "risk_control_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("risks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("controls.id"), nullable=False),
        sa.UniqueConstraint("risk_id", "control_id", name="uq_risk_control_link"),
    )
    op.create_index("ix_risk_control_links_tenant_id", "risk_control_links", ["tenant_id"])
    _add_rls("risk_control_links")


def downgrade() -> None:
    op.drop_table("risk_control_links")
    op.drop_table("risks")
    op.execute("DROP TYPE risk_status")
    op.execute("DROP TYPE risk_level_residual")
    op.execute("DROP TYPE risk_level_inherent")
    op.execute("DROP TYPE treatment_decision")
    op.drop_table("assets")
    op.execute("DROP TYPE asset_category")
    op.drop_table("soa_entries")
    op.execute("DROP TYPE soa_implementation_status")
