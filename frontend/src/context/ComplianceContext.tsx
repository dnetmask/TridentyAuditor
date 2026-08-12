import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { useAuth } from "./AuthContext";
import type { ComplianceOverview } from "../api/types";

interface ComplianceContextValue {
  overview: ComplianceOverview | null;
  refresh: () => void;
}

const ComplianceContext = createContext<ComplianceContextValue>({ overview: null, refresh: () => {} });

// Compartido en el shell de la app (ver Layout.tsx) para que cualquier
// pantalla que agregue evidencia (SoA, asistente, documentos) pueda avisarle
// al indicador de la barra superior que se recalcule, sin esperar a un
// refresco de página.
export function ComplianceProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth();
  const [overview, setOverview] = useState<ComplianceOverview | null>(null);

  const refresh = useCallback(() => {
    if (!session || session.role === "super_admin") {
      setOverview(null);
      return;
    }
    api.complianceOverview(session.token).then(setOverview).catch(() => {});
  }, [session]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(() => ({ overview, refresh }), [overview, refresh]);

  return <ComplianceContext.Provider value={value}>{children}</ComplianceContext.Provider>;
}

export function useCompliance(): ComplianceContextValue {
  return useContext(ComplianceContext);
}
