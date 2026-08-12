import type { FindingClassification } from "../api/types";

const LABELS: Record<FindingClassification, string> = {
  major_nc: "No conformidad mayor",
  minor_nc: "No conformidad menor",
  observation: "Observación",
  improvement: "Oportunidad de mejora",
};

// Reutiliza la escala de color de RiskLevelBadge: mayor≈crítico, menor≈alto,
// observación≈medio, mejora≈bajo — misma lógica de severidad, otro dominio.
const LEVEL: Record<FindingClassification, string> = {
  major_nc: "critical",
  minor_nc: "high",
  observation: "medium",
  improvement: "low",
};

export function FindingClassificationBadge({ classification }: { classification: FindingClassification }) {
  return <span className={`badge badge-risk-${LEVEL[classification]}`}>{LABELS[classification]}</span>;
}
