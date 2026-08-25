import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Area(Base):
    """El área encargada de un documento, proceso o control documentado.

    Definición acordada en la ruta (Fase 1): un solo concepto — no se modela
    "sede" por separado. En la Fase 1 clasifica y filtra documentos; en la
    Fase 2 su ``manager_user_id`` firma el paso "gerente de área" de la
    aprobación multinivel. Vive en el plano de datos del tenant, con RLS,
    igual que ``Asset``.
    """

    __tablename__ = "areas"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_area_tenant_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
