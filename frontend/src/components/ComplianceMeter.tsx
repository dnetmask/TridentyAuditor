import { useCompliance } from "../context/ComplianceContext";

function levelClass(percentage: number): string {
  if (percentage >= 75) return "compliance-high";
  if (percentage >= 40) return "compliance-mid";
  return "compliance-low";
}

// Indicador siempre visible del avance de cumplimiento — vive en
// Layout.tsx, en la franja superior fija del área de contenido (no dentro
// del sidebar, que se puede colapsar), para que el tenant lo vea sin
// importar en qué pantalla esté ni si el menú lateral está expandido o no
// (ver ComplianceContext.tsx para el porqué del cálculo).
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
      <span className="compliance-meter-label">{pct}% cumplimiento</span>
    </div>
  );
}
