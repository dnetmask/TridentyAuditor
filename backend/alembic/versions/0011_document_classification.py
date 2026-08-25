"""Fase 1 — áreas, clasificación/fechas de documentos, M2M documento-control,
rechazo con motivo, derogación y hash de integridad.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
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
    # --- Áreas: el área encargada del documento/proceso/control ---
    op.create_table(
        "areas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "manager_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_area_tenant_name"),
    )
    op.create_index("ix_areas_tenant_id", "areas", ["tenant_id"])
    _add_rls("areas")

    # --- M2M documento <-> control (mismo patrón que risk_control_links) ---
    op.create_table(
        "document_control_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("control_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("controls.id"), nullable=False),
        sa.UniqueConstraint("document_id", "control_id", name="uq_document_control_link"),
    )
    op.create_index("ix_document_control_links_tenant_id", "document_control_links", ["tenant_id"])
    _add_rls("document_control_links")

    # Migrar el antiguo control_id de un-solo-control al M2M antes de soltarlo.
    # gen_random_uuid() es nativo en Postgres 13+.
    op.execute(
        """
        INSERT INTO document_control_links (id, tenant_id, document_id, control_id)
        SELECT gen_random_uuid(), tenant_id, id, control_id
        FROM documents
        WHERE control_id IS NOT NULL
        """
    )
    op.drop_column("documents", "control_id")

    # --- Clasificación, fechas, origen y derogación en Document ---
    op.add_column(
        "documents",
        sa.Column(
            "area_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("areas.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("documents", sa.Column("implementation_date", sa.Date(), nullable=True))
    op.add_column("documents", sa.Column("review_frequency_months", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("next_review_date", sa.Date(), nullable=True))
    document_origin = postgresql.ENUM("internal", "external", name="document_origin", create_type=True)
    document_origin.create(op.get_bind())
    op.add_column(
        "documents",
        sa.Column("origin", document_origin, nullable=False, server_default="internal"),
    )
    op.add_column("documents", sa.Column("external_source", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("documents", sa.Column("retired_by", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("retirement_reason", sa.Text(), nullable=True))

    # --- Integridad y rechazo con rastro en DocumentVersion ---
    op.add_column("document_versions", sa.Column("file_sha256", sa.String(64), nullable=True))
    op.add_column("document_versions", sa.Column("rejected_by", sa.String(255), nullable=True))
    op.add_column("document_versions", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("document_versions", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("document_versions", "rejection_reason")
    op.drop_column("document_versions", "rejected_at")
    op.drop_column("document_versions", "rejected_by")
    op.drop_column("document_versions", "file_sha256")

    # Restaurar el control_id de un-solo-control con el primer enlace del M2M
    # (si un documento llegó a tener varios, se conserva uno — el modelo viejo
    # no podía representar más).
    op.add_column(
        "documents",
        sa.Column(
            "control_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("controls.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE documents d
        SET control_id = (
            SELECT l.control_id FROM document_control_links l
            WHERE l.document_id = d.id
            LIMIT 1
        )
        """
    )

    op.drop_column("documents", "retirement_reason")
    op.drop_column("documents", "retired_by")
    op.drop_column("documents", "retired_at")
    op.drop_column("documents", "external_source")
    op.drop_column("documents", "origin")
    op.execute("DROP TYPE document_origin")
    op.drop_column("documents", "next_review_date")
    op.drop_column("documents", "review_frequency_months")
    op.drop_column("documents", "implementation_date")
    op.drop_column("documents", "area_id")

    op.drop_table("document_control_links")
    op.drop_table("areas")
