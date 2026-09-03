import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.legal.models import LegalComplianceRating, LegalRequirementStatus, LegalRequirementType


class LegalRequirementCreate(BaseModel):
    requirement_type: LegalRequirementType = LegalRequirementType.OTHER
    name: str = Field(min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1800, le=2200)
    articles: str | None = Field(default=None, max_length=255)
    description: str | None = None
    topic: str | None = Field(default=None, max_length=255)
    responsible_user_id: uuid.UUID | None = None
    evidence_document_id: uuid.UUID | None = None
    application_evidence: str | None = None
    review_frequency_months: int | None = Field(default=None, ge=1)
    next_review_date: date | None = None
    expiration_date: date | None = None


class LegalRequirementUpdate(BaseModel):
    """PATCH parcial — solo los campos enviados cambian."""

    requirement_type: LegalRequirementType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    issuer: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1800, le=2200)
    articles: str | None = Field(default=None, max_length=255)
    description: str | None = None
    topic: str | None = Field(default=None, max_length=255)
    responsible_user_id: uuid.UUID | None = None
    evidence_document_id: uuid.UUID | None = None
    application_evidence: str | None = None
    review_frequency_months: int | None = Field(default=None, ge=1)
    next_review_date: date | None = None
    expiration_date: date | None = None
    status: LegalRequirementStatus | None = None
    compliance_rating: LegalComplianceRating | None = None


class LegalRequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requirement_type: LegalRequirementType
    name: str
    issuer: str | None
    publication_year: int | None
    articles: str | None
    description: str | None
    topic: str | None
    responsible_user_id: uuid.UUID | None
    evidence_document_id: uuid.UUID | None
    application_evidence: str | None
    review_frequency_months: int | None
    next_review_date: date | None
    expiration_date: date | None
    status: LegalRequirementStatus
    compliance_rating: LegalComplianceRating
    created_at: datetime
    updated_at: datetime


class LegalSummaryRead(BaseModel):
    """Nivel de cumplimiento de la matriz — solo sobre requisitos vigentes."""

    total: int
    compliant: int
    partial: int
    non_compliant: int
    not_evaluated: int
    percentage: float
