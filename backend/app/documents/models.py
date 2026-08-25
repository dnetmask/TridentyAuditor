import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    OBSOLETE = "obsolete"


class DocumentOrigin(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class Document(Base):
    """MOD·DOC — la base sobre la que cuelga la evidencia de los demás módulos.

    ``tenant_id`` no lleva ForeignKey explícito a ``tenants.id``: la tabla
    ``tenants`` vive en el plano de control (sin RLS) y esta tabla vive en el
    plano de datos del tenant (con RLS) — cruzar esa frontera con una FK
    forzaría a toda consulta a tocar una tabla fuera del alcance del tenant.
    El aislamiento real lo da la política RLS, no una FK.
    """

    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("tenant_id", "code", name="uq_document_tenant_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Clasificación y fechas (Fase 1) ---
    area_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("areas.id", ondelete="SET NULL"), nullable=True
    )
    implementation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Revisión periódica programada (ISO 27001 cl. 7.5): frecuencia en meses +
    # próxima fecha. Al aprobar una versión, si hay frecuencia, la próxima
    # revisión se recalcula sola. "Días para revisión" se calcula en vivo
    # (hoy → next_review_date), nunca se guarda un contador que se
    # desactualiza solo.
    review_frequency_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Documentos de origen externo (normas, contratos, manuales de proveedor)
    # — ISO 7.5.3 exige identificarlos y controlarlos explícitamente.
    origin: Mapped[DocumentOrigin] = mapped_column(
        SAEnum(
            DocumentOrigin,
            name="document_origin",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentOrigin.INTERNAL,
    )
    external_source: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # --- Derogación (retiro formal del documento completo, con motivo) ---
    retired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retired_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retirement_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    area: Mapped["Area"] = relationship()  # noqa: F821 - registrado por app.areas.models
    versions: Mapped[list["DocumentVersion"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )
    control_links: Mapped[list["DocumentControlLink"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def control_ids(self) -> list[uuid.UUID]:
        return [link.control_id for link in self.control_links]

    @property
    def controls(self) -> list:
        return [link.control for link in self.control_links]


class DocumentControlLink(Base):
    """Qué controles del motor de frameworks responde un documento (M2M).

    Mismo patrón que ``RiskControlLink``: ``tenant_id`` denormalizado para
    que la política RLS no tenga que hacer join. Reemplaza al antiguo
    ``Document.control_id`` de un-solo-control, que nunca se usó desde el
    frontend.
    """

    __tablename__ = "document_control_links"
    __table_args__ = (UniqueConstraint("document_id", "control_id", name="uq_document_control_link"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id"), nullable=False)

    document: Mapped["Document"] = relationship(back_populates="control_links")
    control: Mapped["Control"] = relationship()  # noqa: F821 - registrado por app.frameworks.models


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="uq_docversion_document_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DocumentStatus.DRAFT,
    )
    storage_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # SHA-256 del binario, calculado al subir y verificado al servir — la
    # prueba de que el archivo aprobado es el archivo entregado. Nullable
    # solo por las versiones anteriores a la Fase 1.
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Rechazo con rastro: quién, cuándo y por qué — sin esto el control de
    # cambios de ISO 7.5.3.e queda cojo.
    rejected_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped["Document"] = relationship(back_populates="versions")
