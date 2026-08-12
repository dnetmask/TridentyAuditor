import type { RiskLevel } from "../api/types";

const LABELS: Record<RiskLevel, string> = {
  low: "Bajo",
  medium: "Medio",
  high: "Alto",
  critical: "Crítico",
};

export function RiskLevelBadge({ level }: { level: RiskLevel }) {
  return <span className={`badge badge-risk-${level}`}>{LABELS[level]}</span>;
}
