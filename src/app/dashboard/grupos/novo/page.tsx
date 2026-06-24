"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function NovoGrupoPage() {
  const router = useRouter();

  // Estados dos campos de texto
  const [nome, setNome] = useState("");
  const [coordenador, setCoordenador] = useState("");
  const [diaReuniao, setDiaReuniao] = useState("");
  const [paroquia, setParoquia] = useState("");
  const [descricao, setDescricao] = useState("");
  const [status, setStatus] = useState("Ativo");

  // Estado especial para a prévia da imagem da logo
  const [logoPreview, setLogoPreview] = useState<string | null>(null);

  // Função que captura o arquivo escolhido e cria a prévia na tela
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const previewUrl = URL.createObjectURL(file);
      setLogoPreview(previewUrl);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // 1. Cria o objeto do novo grupo
    const novoGrupo = {
      id: Date.now(), // Gera um ID único
      nome, 
      coordenador, 
      membros: 1, // Começa com 1 membro (o próprio coordenador)
      diaReuniao, 
      paroquia, 
      descricao, 
      status,
      logo: logoPreview // Salva a URL temporária da imagem!
    };

    // 2. Puxa os grupos que já existem na memória do navegador
    const gruposSalvos = JSON.parse(localStorage.getItem("novosGrupos") || "[]");
    
    // 3. Adiciona o novo grupo na lista e salva
    gruposSalvos.push(novoGrupo);
    localStorage.setItem("novosGrupos", JSON.stringify(gruposSalvos));
    
    // 4. Volta para a lista de grupos
    router.push("/dashboard/grupos");
  };

  return (
    <div className="max-w-3xl mx-auto pb-12">
      <header className="mb-8">
        <div className="flex items-center gap-4 mb-2">
          <Link href="/dashboard/grupos" className="text-slate-400 hover:text-blue-600 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
          </Link>
          <h1 className="text-3xl font-bold text-slate-800">Novo Grupo</h1>
        </div>
        <p className="text-slate-500 ml-10">Cadastre um novo grupo, ministério ou equipe de trabalho.</p>
      </header>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <form onSubmit={handleSubmit} className="p-6 md:p-8 space-y-8">
          
          {/* SESSÃO 1: Identidade Visual (Upload de Logo) */}
          <section className="flex flex-col md:flex-row gap-6 items-center border-b border-slate-100 pb-8">
            <div className="shrink-0">
              {logoPreview ? (
                // Exibe a imagem escolhida
                <div className="w-32 h-32 rounded-full border-4 border-white shadow-lg overflow-hidden relative group">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={logoPreview} alt="Prévia da Logo" className="w-full h-full object-cover" />
                  <label className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">
                    <span className="text-white text-xs font-semibold">Trocar Imagem</span>
                    <input type="file" accept="image/*" onChange={handleImageChange} className="hidden" />
                  </label>
                </div>
              ) : (
                // Exibe o botão de upload pontilhado
                <label className="w-32 h-32 rounded-full border-2 border-dashed border-slate-300 flex flex-col items-center justify-center bg-slate-50 cursor-pointer hover:bg-slate-100 hover:border-blue-400 transition-colors">
                  <svg className="w-8 h-8 text-slate-400 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                  <span className="text-xs font-medium text-slate-500">Subir Logo</span>
                  <input type="file" accept="image/*" onChange={handleImageChange} className="hidden" />
                </label>
              )}
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-800">Logo do Grupo</h2>
              <p className="text-sm text-slate-500 mt-1">Recomendamos imagens quadradas (1:1) em formato PNG ou JPG de até 2MB. Se não enviar, um ícone padrão será usado.</p>
            </div>
          </section>

          {/* SESSÃO 2: Dados Principais */}
          <section className="space-y-5 border-b border-slate-100 pb-8">
            <h2 className="text-lg font-bold text-slate-800">Informações Gerais</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-slate-700 mb-1">Nome do Grupo/Ministério *</label>
                <input type="text" required value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ex: Grupo de Jovens São João" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-800" />
              </div>
              
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">Nome do Coordenador(a) *</label>
                <input type="text" required value={coordenador} onChange={(e) => setCoordenador(e.target.value)} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-800" />
              </div>

              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">Status</label>
                <select value={status} onChange={(e) => setStatus(e.target.value)} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white text-slate-800">
                  <option value="Ativo">Ativo</option>
                  <option value="Inativo">Inativo</option>
                </select>
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-slate-700 mb-1">Breve Descrição</label>
                <textarea rows={3} value={descricao} onChange={(e) => setDescricao(e.target.value)} placeholder="Qual o propósito e as atividades principais deste grupo?" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-800 resize-none"></textarea>
              </div>
            </div>
          </section>

          {/* SESSÃO 3: Encontros */}
          <section className="space-y-5">
            <h2 className="text-lg font-bold text-slate-800">Local e Horário</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">Dia e Horário da Reunião *</label>
                <input type="text" required value={diaReuniao} onChange={(e) => setDiaReuniao(e.target.value)} placeholder="Ex: Sábados, 16h" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-800" />
              </div>
              
              <div>
                <label className="block text-sm font-bold text-slate-700 mb-1">Paróquia / Local *</label>
                <input type="text" required value={paroquia} onChange={(e) => setParoquia(e.target.value)} placeholder="Ex: Paróquia São João Batista" className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-slate-800" />
              </div>
            </div>
          </section>

          {/* Botões de Ação */}
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-100">
            <Link href="/dashboard/grupos" className="px-5 py-2.5 text-slate-600 font-bold hover:bg-slate-100 rounded-lg transition-colors">
              Cancelar
            </Link>
            <button type="submit" className="px-6 py-2.5 bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
              Criar Grupo
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}