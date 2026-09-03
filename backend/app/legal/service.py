"""MOD·LEG — lógica de la matriz de requisitos legales."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.legal.models import LegalComplianceRating, LegalRequirement, LegalRequirementStatus


def compliance_summary(db: Session, tenant_id: str) -> dict:
    """Nivel de cumplimiento de la matriz, solo sobre requisitos VIGENTES.

    ``partial`` pesa medio punto: cumplir a medias no es cumplir, pero
    tampoco es cero. Los derogados no cuentan — dejaron de ser exigibles.
    """
    requirements = list(
        db.scalars(
            select(LegalRequirement).where(
                LegalRequirement.tenant_id == tenant_id,
                LegalRequirement.status == LegalRequirementStatus.IN_FORCE,
            )
        )
    )
    counts = {rating: 0 for rating in LegalComplianceRating}
    for requirement in requirements:
        counts[requirement.compliance_rating] += 1
    total = len(requirements)
    score = counts[LegalComplianceRating.COMPLIANT] + 0.5 * counts[LegalComplianceRating.PARTIAL]
    percentage = round(score * 100 / total, 1) if total else 0.0
    return {
        "total": total,
        "compliant": counts[LegalComplianceRating.COMPLIANT],
        "partial": counts[LegalComplianceRating.PARTIAL],
        "non_compliant": counts[LegalComplianceRating.NON_COMPLIANT],
        "not_evaluated": counts[LegalComplianceRating.NOT_EVALUATED],
        "percentage": percentage,
    }
