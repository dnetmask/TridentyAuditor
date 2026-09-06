import calendar
import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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


class DispositionAction(str, enum.Enum):
    """Qué se hizo con el documento al cumplir su retención (Fase 5)."""

    ARCHIVE = "archive"
    DESTROY = "destroy"


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

    # --- Retención y disposición final (Fase 5) ---
    # ``retention_months`` (arriba) + la fecha base marcan cuándo el documento
    # cumple su periodo de retención y puede disponerse (archivar/destruir).
    # ``legal_hold`` congela esa disposición: mientras esté activo, el
    # documento no puede disponerse aunque venza su retención (litigio,
    # requerimiento regulatorio).
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disposed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    disposition_action: Mapped[DispositionAction | None] = mapped_column(
        SAEnum(
            DispositionAction,
            name="document_disposition_action",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    disposition_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    def disposition_date(self) -> date | None:
        """Fecha en que cumple retención y puede disponerse (Fase 5).

        Base = aprobación de la versión vigente (o derogación, si aplica) +
        ``retention_months``. Sin retención, no vence. Se calcula en vivo,
        igual que ``next_review_date`` se muestra sin guardar un contador.
        """
        if not self.retention_months:
            return None
        if self.retired_at is not None:
            base = self.retired_at.date()
        else:
            approved = [v for v in self.versions if v.status == DocumentStatus.APPROVED]
            version = max(approved, key=lambda v: v.version_number) if approved else None
            if version is None or version.approved_at is None:
                return None
            base = version.approved_at.date()
        total = base.month - 1 + self.retention_months
        year = base.year + total // 12
        month = total % 12 + 1
        day = min(base.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

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


class ApprovalStep(str, enum.Enum):
    """Pasos de la aprobación multinivel (Fase 2), en orden de firma.

    ``AREA_MANAGER`` solo aplica si el documento tiene área asignada — firma
    el ``manager_user_id`` del área (o un Admin del tenant en su lugar).
    ``SECURITY`` (seguridad de la información) siempre es obligatorio y
    siempre es la última firma: es la que publica.
    """

    AREA_MANAGER = "area_manager"
    SECURITY = "security"


class DocumentApproval(Base):
    """Una firma de la aprobación multinivel — el sello verificable (Fase 2).

    Cada firma guarda el SHA-256 del binario EN EL MOMENTO de firmar: el
    sello queda amarrado al archivo exacto que se aprobó, no al registro
    mutable de la versión. Las firmas de una versión rechazada se eliminan
    (la bitácora conserva el rastro); una versión aprobada las conserva
    para siempre.
    """

    __tablename__ = "document_approvals"
    __table_args__ = (
        UniqueConstraint("version_id", "step", name="uq_document_approval_version_step"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    step: Mapped[ApprovalStep] = mapped_column(
        SAEnum(
            ApprovalStep,
            name="document_approval_step",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    # Email como texto inmutable (igual que approved_by/created_by) + el UUID
    # del firmante para poder cruzar contra el directorio mientras exista.
    signed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    signed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Nullable solo por versiones anteriores a la Fase 1 que no tienen hash.
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    version: Mapped["DocumentVersion"] = relationship(back_populates="approvals")


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
    approvals: Mapped[list["DocumentApproval"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
        order_by="DocumentApproval.signed_at",
    )


class DocumentAcknowledgment(Base):
    """Acuse de recibo "leído y entendido" (Fase 5) — copias controladas.

    Publicar una versión APROBADA a un conjunto de usuarios crea un acuse
    pendiente por cada uno; el usuario lo marca como leído. Es la evidencia
    que el auditor pide para toda política: no basta con publicar, hay que
    demostrar que la gente la leyó (el "obligatorios sin leer" de un gestor
    documental comercial). El acuse apunta a la VERSIÓN, no solo al
    documento: aprobar una versión nueva exige volver a acusar recibo.
    """

    __tablename__ = "document_acknowledgments"
    __table_args__ = (
        UniqueConstraint("version_id", "user_id", name="uq_document_ack_version_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    assigned_by: Mapped[str] = mapped_column(String(255), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
