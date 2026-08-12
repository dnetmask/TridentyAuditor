import uuid

from pydantic import BaseModel, ConfigDict


class RequirementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    text: str
    order_index: int


class ControlRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    evidence_guidance: str | None
    order_index: int


class ControlDetailRead(ControlRead):
    requirements: list[RequirementRead] = []


class DomainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    order_index: int


class DomainDetailRead(DomainRead):
    controls: list[ControlRead] = []


class FrameworkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    version: str


class FrameworkDetailRead(FrameworkRead):
    domains: list[DomainDetailRead] = []
