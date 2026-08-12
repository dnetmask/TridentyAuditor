import type { DocumentStatus } from "../api/types";

const LABELS: Record<DocumentStatus, string> = {
  draft: "Borrador",
  in_review: "En revisión",
  approved: "Aprobado",
  obsolete: "Obsoleto",
};

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return <span className={`badge badge-${status}`}>{LABELS[status]}</span>;
}
