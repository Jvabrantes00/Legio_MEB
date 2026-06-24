"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

export default function GruposPage() {
  const gruposOriginais = [
    { 
      id: 1, 
      nome: "Grupo de Jovens São João", 
      coordenador: "Lucas Fernandes", 
      membros: 15, 
      diaReuniao: "Sábado, 16h", 
      status: "Ativo",
      descricao: "Grupo focado na perseverança pós-encontro e ações sociais na paróquia.",
      paroquia: "Paróquia São João Batista",
      logo: "https://ui-avatars.com/api/?name=Grupo+Sao+Joao&background=0D8ABC&color=fff"
    },
    { 
      id: 2, 
      nome: "Equipe de Canto", 
      coordenador: "Mariana Souza", 
      membros: 8, 
      diaReuniao: "Quarta, 19h", 
      status: "Ativo",
      descricao: "Ministério responsável pela animação musical dos encontros e missas.",
      paroquia: "Paróquia Nossa Sra. do Carmo",
      logo: null
    },
    { 
      id: 3, 
      nome: "Intercessão", 
      coordenador: "Pedro Almeida", 
      membros: 12, 
      diaReuniao: "Segunda, 20h", 
      status: "Ativo",
      descricao: "Equipe dedicada à oração contínua pelo movimento e seus membros.",
      paroquia: "Paróquia São João Batista",
      logo: "https://ui-avatars.com/api/?name=Intercessao&background=10B981&color=fff"
    },
  ];

  const [busca, setBusca] = useState("");
  const [listaCompleta, setListaCompleta] = useState(gruposOriginais);

  // Busca os novos grupos na memória assim que a tela carrega
  useEffect(() => {
    const gruposSalvos = JSON.parse(localStorage.getItem("novosGrupos") || "[]");
    if (gruposSalvos.length > 0) {
      // Coloca os novos grupos no topo da lista
      setListaCompleta([...gruposSalvos, ...gruposOriginais]);
    }
  }, []);

  const gruposFiltrados = listaCompleta.filter((grupo) => {
    const termo = busca.toLowerCase();
    return (
      grupo.nome.toLowerCase().includes(termo) ||
      grupo.coordenador.toLowerCase().includes(termo) ||
      grupo.paroquia.toLowerCase().includes(termo)
    );
  });

  return (
    <>
      <header className="flex flex-col md:flex-row md:justify-between md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Grupos e Equipes</h1>
          <p className="text-slate-500 mt-1">Gerencie os ministérios e grupos pós-encontro.</p>
        </div>
        <Link 
          href="/dashboard/grupos/novo" 
          className="bg-blue-600 text-white font-semibold py-2 px-5 rounded-lg hover:bg-blue-700 transition-colors shadow-sm w-full md:w-auto inline-block text-center"
        >
          + Novo Grupo
        </Link>
      </header>

      <div className="mb-8 max-w-md relative flex items-center">
        <span className="absolute left-4 text-slate-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
        </span>
        <input
          type="text"
          placeholder="Pesquisar por grupo, coordenador ou paróquia..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="w-full pl-12 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl shadow-sm outline-none focus:ring-2 focus:ring-blue-500 text-black transition-all placeholder-slate-400"
        />
      </div>

      {gruposFiltrados.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {gruposFiltrados.map((grupo) => (
            <div key={grupo.id} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 flex flex-col hover:shadow-md transition-shadow">
              
              <div className="flex items-start gap-4 mb-4">
                <div className="w-14 h-14 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 overflow-hidden shadow-sm">
                  {grupo.logo ? (
                    /* eslint-disable-next-line @next/next/no-img-element */
                    <img src={grupo.logo} alt={`Logo ${grupo.nome}`} className="w-full h-full object-cover" />
                  ) : (
                    <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                    </svg>
                  )}
                </div>

                <div className="flex-grow flex justify-between items-start">
                  <h3 className="text-lg font-bold text-slate-800 leading-tight pr-2">
                    {grupo.nome}
                  </h3>
                  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wide whitespace-nowrap mt-1 ${
                    grupo.status === 'Ativo' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {grupo.status}
                  </span>
                </div>
              </div>

              <p className="text-sm text-slate-500 mb-6 flex-grow">
                {grupo.descricao}
              </p>

              <div className="space-y-3 mb-6 bg-slate-50 p-4 rounded-xl border border-slate-100">
                <div className="flex items-center text-sm">
                  <svg className="w-4 h-4 text-slate-400 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                  <span className="text-slate-600 truncate">{grupo.paroquia}</span>
                </div>
                <div className="flex items-center text-sm">
                  <svg className="w-4 h-4 text-slate-400 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
                  <span className="text-slate-600 truncate">Coord: <strong className="text-slate-800">{grupo.coordenador}</strong></span>
                </div>
                <div className="flex items-center text-sm">
                  <svg className="w-4 h-4 text-slate-400 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                  <span className="text-slate-600">{grupo.diaReuniao}</span>
                </div>
                <div className="flex items-center text-sm">
                  <svg className="w-4 h-4 text-slate-400 mr-2 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
                  <span className="text-slate-600">{grupo.membros} participantes</span>
                </div>
              </div>

              <div className="mt-auto pt-4 border-t border-slate-100 flex justify-end">
                <button className="text-blue-600 text-sm font-semibold hover:text-blue-800 transition-colors">
                  Gerenciar Grupo →
                </button>
              </div>

            </div>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center">
          <p className="text-slate-500 font-medium">Nenhum grupo encontrado para "{busca}"</p>
        </div>
      )}
    </>
  );
}