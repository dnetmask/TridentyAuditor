import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class LegalRequirementType(str, enum.Enum):
    CONSTITUTION = "constitution"
    LAW = "law"
    DECREE = "decree"
    RESOLUTION = "resolution"
    CIRCULAR = "circular"
    STANDARD = "standard"
    CONTRACT = "contract"
    GUIDELINE = "guideline"
    OTHER = "other"


class LegalRequirementStatus(str, enum.Enum):
    IN_FORCE = "in_force"  # vigente
    REPEALED = "repealed"  # derogado por el emisor / ya no aplica


class LegalComplianceRating(str, enum.Enum):
    """Calificación de cumplimiento del requisito — la 'Calificación' de la
    matriz. ``PARTIAL`` pesa medio punto en el nivel de cumplimiento."""

    NOT_EVALUATED = "not_evaluated"
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"


class LegalRequirement(Base):
    """MOD·LEG — Matriz de requisitos legales, estatutarios, regulatorios y
    contractuales (ISO 27001 cl. 4 + control A.5.31; para tenants CNO-1960,
    el registro del marco regulatorio del sector).

    Vive en el plano de datos del tenant con RLS, igual que ``Asset`` o
    ``Area``. La evidencia de aplicación apunta a un documento de MOD·DOC —
    el mismo patrón de evidencia del SoA, riesgos y auditoría.
    """

    __tablename__ = "legal_requirements"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_legal_requirement_tenant_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    requirement_type: Mapped[LegalRequirementType] = mapped_column(
        SAEnum(
            LegalRequirementType,
            name="legal_requirement_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LegalRequirementType.OTHER,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # "Ley 1581 de 2012"
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)  # emisor
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    articles: Mapped[str | None] = mapped_column(String(255), nullable=True)  # "Art. 15" / "Toda la ley"
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)  # tema

    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    # Descripción libre de CÓMO se aplica (política X, procedimiento Y) —
    # complementa (no reemplaza) el documento de evidencia vinculado.
    application_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Mismo reloj de revisión programada que en MOD·DOC.
    review_frequency_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Vencimiento del requisito en sí (contratos, permisos); NULL = no vence.
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[LegalRequirementStatus] = mapped_column(
        SAEnum(
            LegalRequirementStatus,
            name="legal_requirement_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LegalRequirementStatus.IN_FORCE,
    )
    compliance_rating: Mapped[LegalComplianceRating] = mapped_column(
        SAEnum(
            LegalComplianceRating,
            name="legal_compliance_rating",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=LegalComplianceRating.NOT_EVALUATED,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
