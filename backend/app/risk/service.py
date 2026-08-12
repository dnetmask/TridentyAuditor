import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.risk.models import Asset, AssetCategory, Risk, RiskControlLink, RiskLevel, RiskStatus, TreatmentDecision


class RiskError(Exception):
    pass


class AssetNotFound(RiskError):
    pass


class RiskNotFound(RiskError):
    pass


def _level_for_score(score: int) -> RiskLevel:
    """Bandas fijas sobre probabilidad × impacto (1-5 cada una, score 1-25).

    "Metodología de valoración configurable" del documento de arquitectura
    queda pendiente — ver docs/modules/mod-rsk.md.
    """
    if score <= 4:
        return RiskLevel.LOW
    if score <= 9:
        return RiskLevel.MEDIUM
    if score <= 15:
        return RiskLevel.HIGH
    return RiskLevel.CRITICAL


# --- Activos ---


def create_asset(
    db: Session,
    tenant_id: str,
    *,
    name: str,
    description: str | None,
    category: AssetCategory,
    owner_user_id: uuid.UUID | None,
) -> Asset:
    asset = Asset(tenant_id=tenant_id, name=name, description=description, category=category, owner_user_id=owner_user_id)
    db.add(asset)
    db.flush()
    return asset


def list_assets(db: Session, tenant_id: str) -> list[Asset]:
    return list(db.scalars(select(Asset).where(Asset.tenant_id == tenant_id).order_by(Asset.name)))


def _get_asset(db: Session, tenant_id: str, asset_id: uuid.UUID) -> Asset:
    asset = db.scalars(select(Asset).where(Asset.id == asset_id, Asset.tenant_id == tenant_id)).first()
    if asset is None:
        raise AssetNotFound(str(asset_id))
    return asset


def update_asset(
    db: Session,
    tenant_id: str,
    asset_id: uuid.UUID,
    *,
    name: str | None,
    description: str | None,
    category: AssetCategory | None,
    owner_user_id: uuid.UUID | None,
) -> Asset:
    asset = _get_asset(db, tenant_id, asset_id)
    if name is not None:
        asset.name = name
    if description is not None:
        asset.description = description
    if category is not None:
        asset.category = category
    if owner_user_id is not None:
        asset.owner_user_id = owner_user_id
    db.flush()
    return asset


# --- Riesgos ---


def _set_control_links(db: Session, tenant_id: str, risk_id: uuid.UUID, control_ids: list[uuid.UUID]) -> None:
    db.execute(delete(RiskControlLink).where(RiskControlLink.risk_id == risk_id))
    for control_id in control_ids:
        db.add(RiskControlLink(tenant_id=tenant_id, risk_id=risk_id, control_id=control_id))


def create_risk(
    db: Session,
    tenant_id: str,
    *,
    asset_id: uuid.UUID | None,
    title: str,
    description: str | None,
    threat: str | None,
    vulnerability: str | None,
    likelihood: int,
    impact: int,
    owner_user_id: uuid.UUID | None,
    control_ids: list[uuid.UUID],
) -> Risk:
    score = likelihood * impact
    risk = Risk(
        tenant_id=tenant_id,
        asset_id=asset_id,
        title=title,
        description=description,
        threat=threat,
        vulnerability=vulnerability,
        likelihood=likelihood,
        impact=impact,
        inherent_score=score,
        inherent_level=_level_for_score(score),
        owner_user_id=owner_user_id,
    )
    db.add(risk)
    db.flush()
    _set_control_links(db, tenant_id, risk.id, control_ids)
    db.flush()
    db.refresh(risk)
    return risk


def _risk_query(tenant_id: str):
    return (
        select(Risk)
        .where(Risk.tenant_id == tenant_id)
        .options(selectinload(Risk.control_links))
        .order_by(Risk.inherent_score.desc(), Risk.created_at.desc())
    )


def list_risks(db: Session, tenant_id: str) -> list[Risk]:
    return list(db.scalars(_risk_query(tenant_id)))


def _get_risk(db: Session, tenant_id: str, risk_id: uuid.UUID) -> Risk:
    stmt = (
        select(Risk)
        .where(Risk.id == risk_id, Risk.tenant_id == tenant_id)
        .options(selectinload(Risk.control_links))
    )
    risk = db.scalars(stmt).first()
    if risk is None:
        raise RiskNotFound(str(risk_id))
    return risk


def update_risk(
    db: Session,
    tenant_id: str,
    risk_id: uuid.UUID,
    *,
    asset_id: uuid.UUID | None,
    title: str | None,
    description: str | None,
    threat: str | None,
    vulnerability: str | None,
    likelihood: int | None,
    impact: int | None,
    treatment_decision: TreatmentDecision | None,
    treatment_plan: str | None,
    residual_likelihood: int | None,
    residual_impact: int | None,
    owner_user_id: uuid.UUID | None,
    status: RiskStatus | None,
    evidence_document_id: uuid.UUID | None,
    control_ids: list[uuid.UUID] | None,
) -> Risk:
    risk = _get_risk(db, tenant_id, risk_id)

    if asset_id is not None:
        risk.asset_id = asset_id
    if title is not None:
        risk.title = title
    if description is not None:
        risk.description = description
    if threat is not None:
        risk.threat = threat
    if vulnerability is not None:
        risk.vulnerability = vulnerability
    if likelihood is not None:
        risk.likelihood = likelihood
    if impact is not None:
        risk.impact = impact
    if likelihood is not None or impact is not None:
        risk.inherent_score = risk.likelihood * risk.impact
        risk.inherent_level = _level_for_score(risk.inherent_score)

    if treatment_decision is not None:
        risk.treatment_decision = treatment_decision
    if treatment_plan is not None:
        risk.treatment_plan = treatment_plan
    if residual_likelihood is not None:
        risk.residual_likelihood = residual_likelihood
    if residual_impact is not None:
        risk.residual_impact = residual_impact
    if residual_likelihood is not None or residual_impact is not None:
        if risk.residual_likelihood is not None and risk.residual_impact is not None:
            risk.residual_score = risk.residual_likelihood * risk.residual_impact
            risk.residual_level = _level_for_score(risk.residual_score)

    if owner_user_id is not None:
        risk.owner_user_id = owner_user_id
    if status is not None:
        risk.status = status
    if evidence_document_id is not None:
        risk.evidence_document_id = evidence_document_id
    if control_ids is not None:
        _set_control_links(db, tenant_id, risk.id, control_ids)

    db.flush()
    db.refresh(risk)
    return risk
