"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

export default function DashboardPage() {
  // Estado para guardar os totais que vamos calcular
  const [metricas, setMetricas] = useState({
    totalAlpinistas: 0,
    pendentes: 0,
    totalGrupos: 0,
  });

  // Estado para listar as inscrições mais recentes que vieram do site
  const [inscricoesRecentes, setInscricoesRecentes] = useState<any[]>([]);

  useEffect(() => {
    // 1. Quantidade base que já tínhamos "chumbado" no código antes
    const qtdBaseAlpinistas = 3; 
    const qtdBaseGrupos = 4;

    // 2. Busca o que o usuário cadastrou no protótipo (localStorage)
    const novosAlpinistas = JSON.parse(localStorage.getItem("novosAlpinistas") || "[]");
    const novosGrupos = JSON.parse(localStorage.getItem("novosGrupos") || "[]");

    // 3. Faz as contas
    const pendentesCount = novosAlpinistas.filter((a: any) => a.status === "Pendente").length;
    
    setMetricas({
      totalAlpinistas: qtdBaseAlpinistas + novosAlpinistas.length,
      pendentes: pendentesCount,
      totalGrupos: qtdBaseGrupos + novosGrupos.length,
    });

    // 4. Pega só as 3 últimas inscrições para o painel rápido e inverte a ordem (mais novas primeiro)
    const ultimas = novosAlpinistas.filter((a: any) => a.status === "Pendente").slice(-3).reverse();
    setInscricoesRecentes(ultimas);
  }, []);

  return (
    <>
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Visão Geral</h1>
          <p className="text-slate-500 mt-1">Bem-vindo ao painel de gestão do Escalada SIA.</p>
        </div>
        <div className="bg-white px-4 py-2 rounded-lg shadow-sm border border-slate-200 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold text-sm">
            AD
          </div>
          <span className="text-sm font-medium text-slate-700">Admin</span>
        </div>
      </header>

      {/* Cards de Estatísticas Topo */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
        
        {/* Card 1: Total Alpinistas */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center shrink-0">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
          </div>
          <div>
            <h3 className="text-slate-500 text-sm font-bold uppercase tracking-wider">Alpinistas Ativos</h3>
            <p className="text-3xl font-bold text-slate-800 mt-1">{metricas.totalAlpinistas}</p>
          </div>
        </div>

        {/* Card 2: Pendentes (Foco de atenção) */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-yellow-200 bg-gradient-to-br from-yellow-50 to-white flex items-center gap-4">
          <div className="w-12 h-12 bg-yellow-100 text-yellow-600 rounded-xl flex items-center justify-center shrink-0">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          </div>
          <div>
            <h3 className="text-yellow-700 text-sm font-bold uppercase tracking-wider">Inscrições Pendentes</h3>
            <p className="text-3xl font-bold text-slate-800 mt-1">{metricas.pendentes}</p>
          </div>
        </div>

        {/* Card 3: Grupos */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex items-center gap-4">
          <div className="w-12 h-12 bg-green-50 text-green-600 rounded-xl flex items-center justify-center shrink-0">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
          </div>
          <div>
            <h3 className="text-slate-500 text-sm font-bold uppercase tracking-wider">Grupos e Equipes</h3>
            <p className="text-3xl font-bold text-slate-800 mt-1">{metricas.totalGrupos}</p>
          </div>
        </div>

        {/* Card 4: Próximo Evento */}
        <div className="bg-slate-900 p-6 rounded-2xl shadow-md border border-slate-800 flex items-center gap-4 relative overflow-hidden">
          <div className="absolute -right-4 -top-4 w-24 h-24 bg-blue-500 rounded-full blur-2xl opacity-20"></div>
          <div className="w-12 h-12 bg-slate-800 text-blue-400 rounded-xl flex items-center justify-center shrink-0 border border-slate-700 z-10">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
          </div>
          <div className="z-10">
            <h3 className="text-slate-400 text-sm font-bold uppercase tracking-wider">Próximo Evento</h3>
            <p className="text-lg font-bold text-white mt-1 leading-tight">Reunião Geral</p>
            <p className="text-xs text-blue-400 mt-0.5">Sexta-feira, 20:00</p>
          </div>
        </div>

      </div>

      {/* Seção Inferior: Inscrições Pendentes */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex justify-between items-center">
          <div>
            <h2 className="text-lg font-bold text-slate-800">Inscrições Aguardando Aprovação</h2>
            <p className="text-sm text-slate-500 mt-1">Membros que se inscreveram pelo site recentemente.</p>
          </div>
          <Link href="/dashboard/alpinistas" className="text-blue-600 text-sm font-bold hover:underline">
            Ver todos →
          </Link>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <tbody className="divide-y divide-slate-100">
              {inscricoesRecentes.length > 0 ? (
                inscricoesRecentes.map((alpinista) => (
                  <tr key={alpinista.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold">
                          {alpinista.nome.charAt(0)}
                        </div>
                        <div>
                          <div className="font-bold text-slate-800">{alpinista.nome}</div>
                          <div className="text-xs text-slate-500">{alpinista.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 font-medium">
                      {alpinista.telefone}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="px-4 py-1.5 bg-blue-50 text-blue-600 font-bold text-sm rounded-lg hover:bg-blue-100 transition-colors">
                        Avaliar
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-6 py-12 text-center">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-50 mb-3">
                      <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                    </div>
                    <p className="text-slate-500 font-medium">Não há inscrições pendentes no momento.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}