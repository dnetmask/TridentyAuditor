"""Fase 5b — búsqueda de texto completo (tsvector) + plantillas de documentos.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
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
    # --- Búsqueda de texto completo en document_versions ---
    op.add_column("document_versions", sa.Column("content_text", sa.Text(), nullable=True))
    # Columna tsvector generada: Postgres la recalcula sola en cada INSERT/UPDATE
    # de content_text — nada que mantener en la app. Config 'spanish' para
    # lematizar y quitar stopwords en español.
    op.execute(
        """
        ALTER TABLE document_versions
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('spanish', coalesce(content_text, ''))) STORED
        """
    )
    op.create_index(
        "ix_document_versions_content_tsv",
        "document_versions",
        ["content_tsv"],
        postgresql_using="gin",
    )

    # --- Plantillas de documentos ---
    op.create_table(
        "document_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=False, server_default="other"),
        sa.Column("storage_ref", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "name", name="uq_document_template_tenant_name"),
    )
    op.create_index("ix_document_templates_tenant_id", "document_templates", ["tenant_id"])
    _add_rls("document_templates")


def downgrade() -> None:
    op.drop_table("document_templates")
    op.drop_index("ix_document_versions_content_tsv", table_name="document_versions")
    op.drop_column("document_versions", "content_tsv")
    op.drop_column("document_versions", "content_text")
