import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AuditStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class FindingClassification(str, enum.Enum):
    MAJOR_NC = "major_nc"
    MINOR_NC = "minor_nc"
    OBSERVATION = "observation"
    IMPROVEMENT = "improvement"


class FindingStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


def _enum_values(enum_cls):
    return [m.value for m in enum_cls]


class AuditProgram(Base):
    """Una auditoría planeada/ejecutada — el 'programa anual' de MOD·AUD.

    Plano de datos del tenant (RLS). ``domain_id`` es opcional: una auditoría
    puede acotarse a un dominio del Anexo A (ej. "Auditoría A.8 Q1 2026") o
    cubrir todo el SGSI.
    """

    __tablename__ = "audit_programs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("domains.id", ondelete="SET NULL"), nullable=True
    )
    auditor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    executed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[AuditStatus] = mapped_column(
        SAEnum(AuditStatus, name="audit_status", values_callable=_enum_values),
        nullable=False,
        default=AuditStatus.PLANNED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    domain: Mapped["Domain"] = relationship()  # noqa: F821 - registrado por app.frameworks.models
    findings: Mapped[list["AuditFinding"]] = relationship(
        back_populates="audit", cascade="all, delete-orphan"
    )


class AuditFinding(Base):
    """Hallazgo de una auditoría, con el CAPA (causa raíz/acción correctiva)
    guardado en la misma fila — igual patrón que ``Risk`` en MOD·RSK, que
    guarda tratamiento y residual junto al riesgo en vez de en una tabla
    aparte.
    """

    __tablename__ = "audit_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("audit_programs.id", ondelete="CASCADE"), nullable=False
    )
    control_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("controls.id", ondelete="SET NULL"), nullable=True
    )
    classification: Mapped[FindingClassification] = mapped_column(
        SAEnum(FindingClassification, name="finding_classification", values_callable=_enum_values),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # CAPA: causa raíz, acción correctiva, responsable, fecha y evidencia de cierre.
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrective_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[FindingStatus] = mapped_column(
        SAEnum(FindingStatus, name="finding_status", values_callable=_enum_values),
        nullable=False,
        default=FindingStatus.OPEN,
    )
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    audit: Mapped["AuditProgram"] = relationship(back_populates="findings")
    control: Mapped["Control"] = relationship()  # noqa: F821 - registrado por app.frameworks.models
