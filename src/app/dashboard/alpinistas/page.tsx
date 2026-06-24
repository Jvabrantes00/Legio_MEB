"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

export default function AlpinistasPage() {
  const alpinistasOriginais = [
    { id: 1, nome: "Lucas Fernandes", email: "lucas.f@email.com", telefone: "(61) 99999-1111", status: "Ativo" },
    { id: 2, nome: "Mariana Souza", email: "mari.souza@email.com", telefone: "(61) 98888-2222", status: "Ativo" },
    { id: 3, nome: "Pedro Almeida", email: "pedro.al@email.com", telefone: "(61) 97777-3333", status: "Inativo" },
  ];

  const [busca, setBusca] = useState("");
  // Estado para guardar a lista completa (originais + os do site)
  const [listaCompleta, setListaCompleta] = useState(alpinistasOriginais);

  // Assim que a página carrega, ele busca os inscritos do site na memória
  useEffect(() => {
    const inscritosSite = JSON.parse(localStorage.getItem("novosAlpinistas") || "[]");
    if (inscritosSite.length > 0) {
      // Junta os originais com os novos (colocando os novos no topo da lista)
      setListaCompleta([...inscritosSite, ...alpinistasOriginais]);
    }
  }, []);

  const alpinistasFiltrados = listaCompleta.filter((alpinista) => {
    const termo = busca.toLowerCase();
    return (
      alpinista.nome.toLowerCase().includes(termo) ||
      alpinista.email.toLowerCase().includes(termo)
    );
  });

  return (
    <>
      <header className="flex flex-col md:flex-row md:justify-between md:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Alpinistas</h1>
          <p className="text-slate-500 mt-1">Gestão de membros do movimento.</p>
        </div>
        <Link 
          href="/dashboard/alpinistas/novo" 
          className="bg-blue-600 text-white font-semibold py-2 px-5 rounded-lg hover:bg-blue-700 transition-colors shadow-sm w-full md:w-auto inline-block text-center"
        >
          + Novo Alpinista
        </Link>
      </header>

      <div className="mb-6 max-w-md relative flex items-center">
        <span className="absolute left-4 text-slate-400">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        </span>
        <input
          type="text"
          placeholder="Pesquisar por nome ou e-mail..."
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="w-full pl-12 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl shadow-sm outline-none focus:ring-2 focus:ring-blue-500 text-black transition-all placeholder-slate-400"
        />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 text-sm uppercase tracking-wider">
                <th className="px-6 py-4 font-medium">Nome</th>
                <th className="px-6 py-4 font-medium">Contato</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {alpinistasFiltrados.length > 0 ? (
                alpinistasFiltrados.map((alpinista) => (
                  <tr key={alpinista.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-800">{alpinista.nome}</div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-500">
                      <div className="font-medium text-slate-700">{alpinista.email}</div>
                      <div className="text-slate-500 mt-0.5">{alpinista.telefone}</div>
                    </td>
                    <td className="px-6 py-4">
                      {/* Cor condicional para Pendente, Ativo e Inativo */}
                      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        alpinista.status === 'Ativo' ? 'bg-green-100 text-green-700' : 
                        alpinista.status === 'Pendente' ? 'bg-yellow-100 text-yellow-700' : 
                        'bg-red-100 text-red-700'
                      }`}>
                        {alpinista.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right text-sm font-medium">
                      <button className="text-blue-600 hover:text-blue-800 mr-4 transition-colors">Editar</button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-6 py-10 text-center text-slate-400 font-medium bg-slate-50">
                    Nenhum alpinista encontrado.
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