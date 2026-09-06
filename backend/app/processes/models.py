import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Process(Base):
    """MOD·PRC — un proceso del mapa de procesos del tenant (Fase 4).

    Plano de datos del tenant (RLS). Jerarquía simple con ``parent_id`` (un
    nivel de padre → subprocesos); no se modela un árbol de profundidad
    arbitraria con reglas especiales — un proceso puede tener padre y punto.
    Los documentos cuelgan vía ``document_process_links`` (M2M), mismo patrón
    que ``RiskControlLink``.
    """

    __tablename__ = "processes"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_process_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("processes.id", ondelete="SET NULL"), nullable=True
    )
    # Responsable del proceso — usuario del tenant, validado en el router.
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document_links: Mapped[list["DocumentProcessLink"]] = relationship(
        back_populates="process", cascade="all, delete-orphan"
    )

    @property
    def document_ids(self) -> list[uuid.UUID]:
        return [link.document_id for link in self.document_links]


class DocumentProcessLink(Base):
    """Qué documentos pertenecen a un proceso (M2M)."""

    __tablename__ = "document_process_links"
    __table_args__ = (
        UniqueConstraint("process_id", "document_id", name="uq_document_process_link"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processes.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )

    process: Mapped["Process"] = relationship(back_populates="document_links")
