import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ActivityEvent(Base):
    """Bitácora de auditoría de la plataforma — append-only.

    Registra quién hizo qué y cuándo: logins (exitosos y fallidos), altas de
    tenants y usuarios, ciclo de vida documental (crear/enviar/aprobar/
    rechazar/descargar) e instanciaciones de SoA/rutas. Es el "audit trail"
    de la sección 06 del documento de arquitectura ("la herramienta de
    auditoría también se audita") — distinto de MOD·AUD, que son las
    auditorías internas de negocio del tenant.

    Sin UPDATE ni DELETE en ningún service, sin RLS: los eventos del plano de
    control (login de Super Admin, alta de tenants) no tienen tenant, así que
    el filtrado por tenant lo hace el endpoint de consulta, igual que en
    ``users``.
    """

    __tablename__ = "activity_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
