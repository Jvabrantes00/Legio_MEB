import {
  canViewAlpinistas, canViewDashboard, canViewEncontros,
  type SiaSession,
} from "./sia-capabilities";

type NavRoute = "/" | "/alpinistas" | "/encontros";

export function siaNavigation(session: SiaSession | null): Array<{ nome: string; rota: NavRoute }> {
  return [
    ...(canViewDashboard(session) ? [{ nome: "Dashboard", rota: "/" as const }] : []),
    ...(canViewAlpinistas(session) ? [{ nome: "Alpinistas", rota: "/alpinistas" as const }] : []),
    ...(canViewEncontros(session) ? [{ nome: "Encontros", rota: "/encontros" as const }] : []),
  ];
}
