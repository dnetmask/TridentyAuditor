import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
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
  // Sesión con vencimiento (Fase S1): el access token expira y se renueva en
  // silencio con el refresh token. Opcionales para tolerar sesiones viejas
  // guardadas antes de este cambio — esas mueren en el primer 401.
  refreshToken?: string | null;
  expiresAt?: number | null; // epoch ms
}

interface AuthContextValue {
  session: Session | null;
  login: (session: Session) => void;
  logout: () => void;
}

const STORAGE_KEY = "tridentyauditor.session";
// Renovar cuando falten menos de 10 minutos para el vencimiento.
const REFRESH_MARGIN_MS = 10 * 60 * 1000;
const REFRESH_CHECK_MS = 60 * 1000;
// Nunca más de un intento de refresh por ventana: el efecto depende de la
// sesión y cada rotación lo re-dispara — sin este guard, un token más corto
// que el margen entra en bucle, y el doble montaje de StrictMode lanza dos
// refresh en paralelo con el mismo token (el segundo pierde la rotación,
// recibe 401 y cierra la sesión).
const REFRESH_ATTEMPT_COOLDOWN_MS = 30 * 1000;
let lastRefreshAttemptAt = 0;

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
        const refreshToken = session?.refreshToken;
        if (refreshToken) {
          // Revoca la sesión larga en el servidor; si falla (sin red), el
          // refresh token expira solo — cerrar sesión local no debe esperar.
          api.logoutServer(refreshToken).catch(() => {});
        }
        localStorage.removeItem(STORAGE_KEY);
        setSession(null);
      },
    }),
    [session],
  );

  // Cierre de sesión forzado cuando cualquier request autenticado recibe 401
  // (token vencido sin refresh posible, cuenta desactivada, rol revocado).
  useEffect(() => {
    const onExpired = () => {
      localStorage.removeItem(STORAGE_KEY);
      setSession(null);
    };
    window.addEventListener("tridenty:session-expired", onExpired);
    return () => window.removeEventListener("tridenty:session-expired", onExpired);
  }, []);

  // Renovación silenciosa: revisa cada minuto y renueva cuando el access
  // token está por vencer, rotando también el refresh token.
  useEffect(() => {
    if (!session?.refreshToken || !session.expiresAt) return;

    let cancelled = false;
    async function maybeRefresh() {
      if (!session?.refreshToken || !session.expiresAt) return;
      if (session.expiresAt - Date.now() > REFRESH_MARGIN_MS) return;
      if (Date.now() - lastRefreshAttemptAt < REFRESH_ATTEMPT_COOLDOWN_MS) return;
      lastRefreshAttemptAt = Date.now();
      try {
        const res = await api.refresh(session.refreshToken);
        if (cancelled) return;
        const next: Session = {
          ...session,
          token: res.access_token,
          refreshToken: res.refresh_token,
          expiresAt: Date.now() + res.expires_in * 1000,
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        setSession(next);
      } catch {
        if (cancelled) return;
        localStorage.removeItem(STORAGE_KEY);
        setSession(null);
      }
    }

    maybeRefresh();
    const interval = setInterval(maybeRefresh, REFRESH_CHECK_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
