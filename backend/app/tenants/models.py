import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class IsolationTier(str, enum.Enum):
    """Sección 04 del documento de arquitectura: decisión por tenant, no de plataforma."""

    POOLED = "pooled"
    ISOLATED = "isolated"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    isolation_tier: Mapped[IsolationTier] = mapped_column(
        SAEnum(
            IsolationTier,
            name="isolation_tier",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=IsolationTier.POOLED,
    )
    # Un tenant, una norma — a diferencia de tenant_id en las tablas de MOD·DOC,
    # esta FK sí es real: frameworks vive en el mismo plano sin RLS que
    # tenants, así que no hay frontera de aislamiento que cruzar. Se elige una
    # sola vez al crear el tenant (ver tenants/router.py); si una organización
    # necesita dos normas (ej. ISO 27001 y la Guía de Ciberseguridad del CNO),
    # son dos tenants — sus estructuras de dominios/controles no son
    # compatibles entre sí.
    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    framework: Mapped["Framework"] = relationship()  # noqa: F821 - registrado por app.frameworks.models
