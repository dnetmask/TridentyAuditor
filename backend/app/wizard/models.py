import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class WizardTaskStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"


class WizardPhase(Base):
    """Una fase de la ruta paso a paso de una norma (ISO: "Ruta SGSI", CNO-1960: "Ruta CNO").

    Dato de referencia global, igual que Framework/Domain — no vive por
    tenant, y cargar/editar el checklist no requiere tocar el esquema. Cada
    norma trae su propia ruta (``framework_id``), con su propia numeración de
    fases: no hay una sola metodología universal, la de ISO 27001 (PDCA,
    sección 02 del documento de arquitectura) no encaja con el modelo de
    cumplimiento regulatorio de plazos fijos de CNO-1960 — ver
    ``app/wizard/seeds/cno_route.py``.
    """

    __tablename__ = "wizard_phases"
    __table_args__ = (
        UniqueConstraint("framework_id", "number", name="uq_wizard_phase_framework_number"),
        UniqueConstraint("framework_id", "code", name="uq_wizard_phase_framework_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str] = mapped_column(String(255), nullable=False)

    framework: Mapped["Framework"] = relationship()  # noqa: F821 - registrado por app.frameworks.models
    templates: Mapped[list["WizardTaskTemplate"]] = relationship(
        back_populates="phase", cascade="all, delete-orphan", order_by="WizardTaskTemplate.order_index"
    )


class WizardTaskTemplate(Base):
    """Checklist de referencia por fase — se instancia por tenant al arrancar el ciclo."""

    __tablename__ = "wizard_task_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wizard_phases.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    phase: Mapped["WizardPhase"] = relationship(back_populates="templates")


class TenantWizardTask(Base):
    """Tarea instanciada para un tenant — plano de datos del tenant, con RLS.

    ``template_id`` nulo identifica una tarea agregada a mano por el tenant
    (fuera del checklist de referencia). El unique constraint sobre
    (tenant_id, template_id) permite múltiples filas NULL — Postgres no las
    considera duplicadas — así que no choca con tareas custom, y a la vez
    hace idempotente instanciar el checklist más de una vez.
    """

    __tablename__ = "tenant_wizard_tasks"
    __table_args__ = (
        UniqueConstraint("tenant_id", "template_id", name="uq_tenant_wizard_task_template"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    phase_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wizard_phases.id"), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("wizard_task_templates.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Explicit order, not inferred from created_at: every task instantiated
    # from the checklist is created inside the same transaction, so
    # Postgres' now() — the transaction start time, not per-statement —
    # gives them all an identical created_at and makes ORDER BY created_at
    # non-deterministic.
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[WizardTaskStatus] = mapped_column(
        SAEnum(
            WizardTaskStatus,
            name="wizard_task_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=WizardTaskStatus.PENDING,
    )
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
