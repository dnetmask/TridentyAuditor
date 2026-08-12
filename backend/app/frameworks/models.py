import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Framework(Base):
    """A compliance framework (ISO/IEC 27001:2022, NIST CSF 2.0, ...).

    Frameworks son datos de referencia globales, no datos por tenant —
    cargar un framework nuevo es insertar filas, no migrar esquema (sección
    03 del documento de arquitectura).
    """

    __tablename__ = "frameworks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)

    domains: Mapped[list["Domain"]] = relationship(
        back_populates="framework", cascade="all, delete-orphan", order_by="Domain.order_index"
    )


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (UniqueConstraint("framework_id", "code", name="uq_domain_framework_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("frameworks.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    framework: Mapped["Framework"] = relationship(back_populates="domains")
    controls: Mapped[list["Control"]] = relationship(
        back_populates="domain", cascade="all, delete-orphan", order_by="Control.order_index"
    )


class Control(Base):
    __tablename__ = "controls"
    __table_args__ = (UniqueConstraint("domain_id", "code", name="uq_control_domain_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Guía práctica de qué evidencia suele demostrar este control (redactada
    # por el equipo, no texto normativo licenciado del estándar — ver nota en
    # app/frameworks/seeds/iso27001_2022.py). Sirve de ejemplo, no reemplaza
    # el criterio del auditor.
    evidence_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    domain: Mapped["Domain"] = relationship(back_populates="controls")
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="control", cascade="all, delete-orphan", order_by="Requirement.order_index"
    )


class Requirement(Base):
    """Optional finer-grained breakdown of a control.

    No se siembra automáticamente junto con ISO/IEC 27001:2022 — el texto
    normativo de los requisitos es contenido licenciado del estándar. Queda
    disponible para cuando el equipo cargue ese texto o para NIST CSF 2.0 en
    la Fase 2.
    """

    __tablename__ = "requirements"
    __table_args__ = (UniqueConstraint("control_id", "code", name="uq_requirement_control_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    control_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("controls.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    control: Mapped["Control"] = relationship(back_populates="requirements")
