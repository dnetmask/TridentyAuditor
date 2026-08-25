import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.frameworks.models import Control


class ImplementationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"


class SoaEntry(Base):
    """MOD·SOA — Declaración de Aplicabilidad, una fila por control y tenant.

    Vive en el plano de datos del tenant (RLS). ``control_id`` apunta al
    motor de frameworks (dato global) — así que cargar NIST CSF 2.0 en
    Fase 2 es, otra vez, una operación de datos: se instancia una SoaEntry
    más por control nuevo, sin tocar este esquema (sección 03).
    """

    __tablename__ = "soa_entries"
    __table_args__ = (UniqueConstraint("tenant_id", "control_id", name="uq_soa_entry_tenant_control"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id"), nullable=False)
    is_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_status: Mapped[ImplementationStatus] = mapped_column(
        SAEnum(
            ImplementationStatus,
            name="soa_implementation_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        nullable=False,
        default=ImplementationStatus.NOT_STARTED,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    control: Mapped["Control"] = relationship()
