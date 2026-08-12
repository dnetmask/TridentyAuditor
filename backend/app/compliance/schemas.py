from pydantic import BaseModel


class ComplianceComponent(BaseModel):
    key: str
    label: str
    evidenced: int
    total: int
    percentage: float


class ComplianceOverview(BaseModel):
    percentage: float
    components: list[ComplianceComponent]
