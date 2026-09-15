"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, Users } from "lucide-react";
import { useSiaSession } from "../../components/SiaSessionProvider";
import { canViewDashboard } from "../../lib/sia-capabilities";
import { dashboardCards, type DashboardStats } from "../../lib/dashboard-contract";
import { siaFetch } from "../../lib/sia-api";

export default function Dashboard() {
  const { session, loading: sessionLoading, error: sessionError } = useSiaSession();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionLoading || !canViewDashboard(session)) return;
    const controller = new AbortController();
    async function load() {
      try {
        const response = await siaFetch("/dashboard-stats/", { signal: controller.signal });
        if (!response.ok) throw new Error("Não foi possível carregar o panorama do sistema.");
        const body: DashboardStats = await response.json();
        if (!controller.signal.aborted) setStats(body);
      } catch (failure) {
        if (!controller.signal.aborted) setError(
          failure instanceof Error ? failure.message : "Panorama indisponível.",
        );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [sessionLoading, session]);

  if (sessionLoading) return <p className="p-10 text-gray-500">Carregando sessão...</p>;
  if (sessionError) return <p className="p-10 text-red-600">{sessionError}</p>;
  if (!canViewDashboard(session)) return <p className="p-10 text-gray-600">Seu papel não permite acessar o dashboard. Use os módulos disponíveis no menu.</p>;
  if (loading) return <p className="p-10 text-gray-500">Carregando panorama do sistema...</p>;
  if (error || !stats) return <p className="p-10 text-red-600">{error || "Panorama indisponível."}</p>;

  const cards = dashboardCards(stats);
  const nextEncounter = stats.proximosEncontros?.[0];

  return <div className="space-y-8">
    <div>
      <h1 className="text-3xl font-bold text-escalada-texto">Bem-vindo, {stats.usuarioLogado}!</h1>
      <p className="text-gray-500 mt-1">Panorama baseado nos dados agregados do servidor.</p>
    </div>

    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {cards.map((card) => <div key={card.label} className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-3 text-escalada-azul mb-2"><Users size={22} /><p className="text-sm font-medium text-gray-500">{card.label}</p></div>
        <p className="text-2xl font-bold text-escalada-texto">{card.value}</p>
      </div>)}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-3 text-escalada-vermelho mb-2"><CalendarDays size={22} /><p className="text-sm font-medium text-gray-500">Próximo Encontro</p></div>
        <p className="text-xl font-bold text-escalada-texto">{nextEncounter?.nome || "Nenhum encontro futuro"}</p>
        {nextEncounter && <p className="text-sm text-gray-500 mt-1">{nextEncounter.data}</p>}
      </div>
    </div>

    <div className="bg-white p-6 rounded-2xl border border-gray-100">
      <h2 className="text-lg font-bold text-escalada-texto mb-3">Consultar módulos</h2>
      <div className="flex flex-wrap gap-4">
        <Link href="/alpinistas" className="text-escalada-azul hover:underline flex items-center gap-1">Alpinistas <ArrowRight size={16} /></Link>
        <Link href="/encontros" className="text-escalada-azul hover:underline flex items-center gap-1">Encontros <ArrowRight size={16} /></Link>
      </div>
    </div>
  </div>;
}
