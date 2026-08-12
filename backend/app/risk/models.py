import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class AssetCategory(str, enum.Enum):
    INFORMATION = "information"
    SOFTWARE = "software"
    HARDWARE = "hardware"
    SERVICE = "service"
    PEOPLE = "people"
    FACILITY = "facility"
    OTHER = "other"


class TreatmentDecision(str, enum.Enum):
    MITIGATE = "mitigate"
    ACCEPT = "accept"
    TRANSFER = "transfer"
    AVOID = "avoid"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskStatus(str, enum.Enum):
    OPEN = "open"
    TREATING = "treating"
    CLOSED = "closed"


def _enum_values(enum_cls):
    return [m.value for m in enum_cls]


class Asset(Base):
    """Inventario de activos — MOD·RSK. Plano de datos del tenant (RLS)."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[AssetCategory] = mapped_column(
        SAEnum(AssetCategory, name="asset_category", values_callable=_enum_values), nullable=False
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Risk(Base):
    """Un riesgo valorado — matriz de riesgo de MOD·RSK.

    La metodología de valoración es fija en esta fase (probabilidad ×
    impacto, ambos 1-5, con bandas de nivel) — "metodología configurable"
    del documento de arquitectura queda pendiente como mejora futura, ver
    docs/modules/mod-rsk.md.
    """

    __tablename__ = "risks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    threat: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vulnerability: Mapped[str | None] = mapped_column(String(255), nullable=True)

    likelihood: Mapped[int] = mapped_column(Integer, nullable=False)
    impact: Mapped[int] = mapped_column(Integer, nullable=False)
    inherent_score: Mapped[int] = mapped_column(Integer, nullable=False)
    inherent_level: Mapped[RiskLevel] = mapped_column(
        SAEnum(RiskLevel, name="risk_level_inherent", values_callable=_enum_values), nullable=False
    )

    treatment_decision: Mapped[TreatmentDecision | None] = mapped_column(
        SAEnum(TreatmentDecision, name="treatment_decision", values_callable=_enum_values), nullable=True
    )
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    residual_likelihood: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_impact: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_level: Mapped[RiskLevel | None] = mapped_column(
        SAEnum(RiskLevel, name="risk_level_residual", values_callable=_enum_values), nullable=True
    )

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[RiskStatus] = mapped_column(
        SAEnum(RiskStatus, name="risk_status", values_callable=_enum_values),
        nullable=False,
        default=RiskStatus.OPEN,
    )
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    control_links: Mapped[list["RiskControlLink"]] = relationship(
        back_populates="risk", cascade="all, delete-orphan"
    )

    @property
    def control_ids(self) -> list[uuid.UUID]:
        return [link.control_id for link in self.control_links]


class RiskControlLink(Base):
    """Qué controles del motor de frameworks tratan un riesgo (M2M)."""

    __tablename__ = "risk_control_links"
    __table_args__ = (UniqueConstraint("risk_id", "control_id", name="uq_risk_control_link"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    risk_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risks.id", ondelete="CASCADE"), nullable=False)
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id"), nullable=False)

    risk: Mapped["Risk"] = relationship(back_populates="control_links")
