import { useCompliance } from "../context/ComplianceContext";

function levelClass(percentage: number): string {
  if (percentage >= 75) return "compliance-high";
  if (percentage >= 40) return "compliance-mid";
  return "compliance-low";
}

// Indicador siempre visible del avance de cumplimiento del SGSI — vive en
// Layout.tsx, junto al menú superior, para que el tenant lo vea sin importar
// en qué pantalla esté (ver ComplianceContext.tsx para el porqué del cálculo).
export function ComplianceMeter() {
  const { overview } = useCompliance();
  if (!overview) return null;

  const pct = Math.round(overview.percentage);
  const tooltip = overview.components
    .map((c) => `${c.label}: ${c.evidenced}/${c.total} (${Math.round(c.percentage)}%)`)
    .join("\n");

  return (
    <div className={`compliance-meter ${levelClass(overview.percentage)}`} title={tooltip}>
      <div className="compliance-meter-bar">
        <div className="compliance-meter-fill" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
      </div>
      <span className="compliance-meter-label">{pct}% cumplimiento SGSI</span>
    </div>
  );
}
