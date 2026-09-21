"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { isSiaSession, type SiaSession } from "../lib/sia-capabilities";
import { readApiError } from "../lib/form-api-error";

interface SessionState {
  session: SiaSession | null;
  loading: boolean;
  error: string | null;
}

const SessionContext = createContext<SessionState>({
  session: null,
  loading: true,
  error: null,
});

export function SiaSessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<SessionState>({
    session: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const response = await fetch("/api/auth/me", {
          cache: "no-store",
          credentials: "same-origin",
          signal: controller.signal,
        });
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar sua sessão."));
        const body: unknown = await response.json();
        if (!isSiaSession(body)) throw new Error("Resposta de sessão inválida.");
        setState({ session: body, loading: false, error: null });
      } catch (error) {
        if (controller.signal.aborted) return;
        setState({
          session: null,
          loading: false,
          error: error instanceof Error ? error.message : "Sessão indisponível.",
        });
      }
    }
    void load();
    return () => controller.abort();
  }, [router]);

  return <SessionContext.Provider value={state}>{children}</SessionContext.Provider>;
}

export function useSiaSession() {
  return useContext(SessionContext);
}
