import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { UserRole } from "../api/types";

export interface Session {
  tenantId: string | null;
  tenantName: string | null;
  frameworkCode: string | null;
  userId: string;
  email: string;
  fullName: string;
  role: UserRole;
  token: string;
}

interface AuthContextValue {
  session: Session | null;
  login: (session: Session) => void;
  logout: () => void;
}

const STORAGE_KEY = "tridentyauditor.session";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function loadStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadStoredSession);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      login: (next) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        setSession(next);
      },
      logout: () => {
        localStorage.removeItem(STORAGE_KEY);
        setSession(null);
      },
    }),
    [session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
