"""MOD·LEG — matriz de requisitos legales (ISO 27001 cl. 4 / A.5.31).

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
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
    requirement_type = postgresql.ENUM(
        "constitution",
        "law",
        "decree",
        "resolution",
        "circular",
        "standard",
        "contract",
        "guideline",
        "other",
        name="legal_requirement_type",
        create_type=False,
    )
    requirement_type.create(op.get_bind())
    requirement_status = postgresql.ENUM(
        "in_force", "repealed", name="legal_requirement_status", create_type=False
    )
    requirement_status.create(op.get_bind())
    compliance_rating = postgresql.ENUM(
        "not_evaluated",
        "compliant",
        "partial",
        "non_compliant",
        name="legal_compliance_rating",
        create_type=False,
    )
    compliance_rating.create(op.get_bind())

    op.create_table(
        "legal_requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_type", requirement_type, nullable=False, server_default="other"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("issuer", sa.String(255), nullable=True),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("articles", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("topic", sa.String(255), nullable=True),
        sa.Column(
            "responsible_user_id",
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
        sa.Column("application_evidence", sa.Text(), nullable=True),
        sa.Column("review_frequency_months", sa.Integer(), nullable=True),
        sa.Column("next_review_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("status", requirement_status, nullable=False, server_default="in_force"),
        sa.Column(
            "compliance_rating", compliance_rating, nullable=False, server_default="not_evaluated"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_legal_requirement_tenant_name"),
    )
    op.create_index("ix_legal_requirements_tenant_id", "legal_requirements", ["tenant_id"])
    _add_rls("legal_requirements")


def downgrade() -> None:
    op.drop_table("legal_requirements")
    op.execute("DROP TYPE legal_compliance_rating")
    op.execute("DROP TYPE legal_requirement_status")
    op.execute("DROP TYPE legal_requirement_type")
