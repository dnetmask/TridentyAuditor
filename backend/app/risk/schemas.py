import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.risk.models import AssetCategory, RiskLevel, RiskStatus, TreatmentDecision


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: AssetCategory
    owner_user_id: uuid.UUID | None = None


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: AssetCategory | None = None
    owner_user_id: uuid.UUID | None = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    category: AssetCategory
    owner_user_id: uuid.UUID | None
    created_at: datetime


class RiskCreate(BaseModel):
    asset_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    threat: str | None = Field(default=None, max_length=255)
    vulnerability: str | None = Field(default=None, max_length=255)
    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)
    owner_user_id: uuid.UUID | None = None
    control_ids: list[uuid.UUID] = []


class RiskUpdate(BaseModel):
    asset_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    threat: str | None = None
    vulnerability: str | None = None
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    treatment_decision: TreatmentDecision | None = None
    treatment_plan: str | None = None
    residual_likelihood: int | None = Field(default=None, ge=1, le=5)
    residual_impact: int | None = Field(default=None, ge=1, le=5)
    owner_user_id: uuid.UUID | None = None
    status: RiskStatus | None = None
    evidence_document_id: uuid.UUID | None = None
    control_ids: list[uuid.UUID] | None = None


class RiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID | None
    title: str
    description: str | None
    threat: str | None
    vulnerability: str | None
    likelihood: int
    impact: int
    inherent_score: int
    inherent_level: RiskLevel
    treatment_decision: TreatmentDecision | None
    treatment_plan: str | None
    residual_likelihood: int | None
    residual_impact: int | None
    residual_score: int | None
    residual_level: RiskLevel | None
    owner_user_id: uuid.UUID | None
    status: RiskStatus
    evidence_document_id: uuid.UUID | None
    control_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime
