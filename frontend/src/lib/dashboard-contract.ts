export interface DashboardStats {
  usuarioLogado: string;
  coordenacoes: string[];
  totalAlpinistas: number;
  proximosEncontros: Array<{ nome: string; data: string }>;
  visaoGeral?: { ativos: number; pendentes: number; inativos: number };
  moduloFichas?: { fichasPendentes: number; alertaFichas: string };
}

export interface DashboardCard {
  label: string;
  value: number;
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

export function dashboardCards(stats: DashboardStats): DashboardCard[] {
  const cards: DashboardCard[] = [];
  if (isCount(stats.totalAlpinistas)) {
    cards.push({ label: "Total de Alpinistas", value: stats.totalAlpinistas });
  }
  if (stats.visaoGeral) {
    for (const [label, value] of [
      ["Membros ativos", stats.visaoGeral.ativos],
      ["Membros pendentes", stats.visaoGeral.pendentes],
      ["Membros inativos", stats.visaoGeral.inativos],
    ] as const) {
      if (isCount(value)) cards.push({ label, value });
    }
  }
  if (isCount(stats.moduloFichas?.fichasPendentes)) {
    cards.push({ label: "Fichas pendentes", value: stats.moduloFichas.fichasPendentes });
  }
  return cards;
}
