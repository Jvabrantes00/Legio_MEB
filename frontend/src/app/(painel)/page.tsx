"use client";

// ============================================================================
// IMPORTAÇÕES
// ============================================================================
import { useState, useEffect } from "react";
import { Users, CalendarDays, Activity, HeartPulse, ArrowRight, Plus } from "lucide-react";
import Link from "next/link"; 

// ============================================================================
// INTERFACE (CONTRATO DE DADOS)
// ============================================================================
// Necessário para mapear os dados reais vindos do Django
interface Alpinista {
    id: number;
    nome: string;
    email: string;
    telefone: string;
    dataNascimento: string; 
    endereco: string;
    nomePai: string;
    telefonePai: string;
    nomeMae: string;
    telefoneMae: string;
    restricaoSaude: string;
    medicacao: string;
    grupo: string;
    status: string;
    foto?: string;
}

export default function Dashboard() {
    
    // ============================================================================
    // ESTADOS DO DASHBOARD
    // ============================================================================
    const [alpinistas, setAlpinistas] = useState<Alpinista[]>([]);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");

    // ============================================================================
    // CICLO DE VIDA (useEffect)
    // ============================================================================
    // Busca os dados automaticamente ao carregar a página inicial
    useEffect(() => {
        buscarDadosGerais();
    }, []);

    // ============================================================================
    // FUNÇÃO DE BUSCA (API REST)
    // ============================================================================
    const getCookie = (nome: string) => {
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; ${nome}=`);
        if (partes.length === 2) return partes.pop()?.split(';').shift();
        return null;
    };

    const buscarDadosGerais = async () => {
        try {
            const token = getCookie('sia_token');
            if (!token) throw new Error("Token de autenticação não encontrado.");

            const resposta = await fetch("http://localhost:8000/api/alpinistas/", {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                }
            });

            if (!resposta.ok) throw new Error("Erro ao carregar os dados do painel.");

            const dados = await resposta.json();
            setAlpinistas(dados);

        } catch (error: any) {
            setErro(error.message);
        } finally {
            setCarregando(false);
        }
    };

    // ============================================================================
    // LÓGICA DE NEGÓCIO: CÁLCULO DAS MÉTRICAS (AGREGAÇÃO)
    // ============================================================================
    
    // 1. Total Absoluto
    const totalAlpinistas = alpinistas.length;
    
    // 2. Filtra apenas os ativos no sistema
    const totalAtivos = alpinistas.filter(a => (a.status || "").toLowerCase() === "ativo").length;
    
    // 3. Conta quantos possuem algo escrito no campo de restrição de saúde
    const totalComRestricao = alpinistas.filter(a => a.restricaoSaude && a.restricaoSaude.trim() !== "").length;
    
    // 4. ÚLTIMAS INSCRIÇÕES PENDENTES (A MÁGICA ACONTECE AQUI)
    // Passo 1: Filtramos APENAS quem tem status "pendente"
    // Passo 2: Invertemos a lista (reverse) para o mais novo ficar no topo
    // Passo 3: Cortamos (slice) para exibir no máximo os 4 primeiros na tela
    const ultimasInscricoesPendentes = alpinistas
        .filter(a => (a.status || "").toLowerCase() === "pendente")
        .reverse()
        .slice(0, 4);

    // ============================================================================
    // RENDERIZAÇÃO DA INTERFACE (JSX / HTML)
    // ============================================================================
    
    // Telas de feedback visual
    if (carregando) return <div className="p-10 text-center text-gray-500 font-medium animate-pulse">Carregando panorama do sistema...</div>;
    if (erro) return <div className="p-10 text-center text-red-500 font-medium bg-red-50 rounded-xl border border-red-100">{erro}</div>;

    return (
        <div className="space-y-8 animate-fade-in">
            
            {/* CABEÇALHO DA PÁGINA */}
            <div>
                <h1 className="text-3xl font-bold text-escalada-texto">Bem-vindo, Vinicius Prado!</h1>
                <p className="text-gray-500 mt-1">Aqui está o panorama atual do Movimento Escalada.</p>
            </div>

            {/* GRID DE CARDS DE RESUMO */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                
                {/* Card 1: Total de Alpinistas */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
                    <div className="p-4 bg-blue-50 text-escalada-azul rounded-xl">
                        <Users className="w-8 h-8" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-500">Total de Alpinistas</p>
                        <h3 className="text-2xl font-bold text-escalada-texto">{totalAlpinistas}</h3>
                    </div>
                </div>

                {/* Card 2: Membros Ativos */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
                    <div className="p-4 bg-green-50 text-green-600 rounded-xl">
                        <Activity className="w-8 h-8" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-500">Membros Ativos</p>
                        <h3 className="text-2xl font-bold text-escalada-texto">{totalAtivos}</h3>
                    </div>
                </div>

                {/* Card 3: Alertas de Saúde */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
                    <div className="p-4 bg-yellow-50 text-yellow-600 rounded-xl">
                        <HeartPulse className="w-8 h-8" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-500">Atenção à Saúde</p>
                        <h3 className="text-2xl font-bold text-escalada-texto">{totalComRestricao}</h3>
                    </div>
                </div>
                
                {/* Card 4: Próximo Encontro */}
                <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
                    <div className="p-4 bg-red-50 text-escalada-vermelho rounded-xl">
                        <CalendarDays className="w-8 h-8" />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-500">Próximo Encontro</p>
                        <h3 className="text-2xl font-bold text-escalada-texto">Em 15 Dias</h3>
                    </div>
                </div>
                
            </div>

            {/* SEÇÃO INFERIOR: TABELA DE APROVAÇÕES E AÇÕES */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* TABELA DINÂMICA (Apenas Pendentes) */}
                <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                    
                    <div className="p-6 border-b border-gray-100 flex justify-between items-center">
                        <div>
                            <h2 className="text-lg font-bold text-escalada-texto">Inscrições Pendentes</h2>
                            <p className="text-xs text-gray-500 mt-1">Alpinistas aguardando aprovação para ativar o cadastro.</p>
                        </div>
                        <Link href="/alpinistas" className="text-sm text-escalada-azul hover:underline flex items-center gap-1 font-medium">
                            Ver todos <ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                    
                    <div className="overflow-x-auto">
                        <table className="w-full text-left">
                            <thead className="bg-gray-50 text-gray-500 text-sm">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Nome do Alpinista</th>
                                    <th className="px-6 py-4 font-medium">E-mail de Contato</th>
                                    <th className="px-6 py-4 font-medium">Status</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100 text-sm">
                                {/* Se não houver nenhum pendente na lista filtrada */}
                                {ultimasInscricoesPendentes.length === 0 ? (
                                    <tr>
                                        <td colSpan={3} className="px-6 py-8 text-center text-gray-500">
                                            Nenhuma inscrição pendente no momento. Tudo em dia! 🎉
                                        </td>
                                    </tr>
                                ) : (
                                    // Mapeia APENAS os dados filtrados como "pendente"
                                    ultimasInscricoesPendentes.map((alpinista) => (
                                        <tr key={alpinista.id} className="hover:bg-gray-50 transition-colors">
                                            <td className="px-6 py-4 font-medium text-escalada-texto flex items-center gap-3">
                                                {alpinista.foto ? (
                                                    <img src={alpinista.foto} alt="Foto" className="w-8 h-8 rounded-full object-cover" />
                                                ) : (
                                                    <div className="w-8 h-8 rounded-full bg-yellow-50 text-yellow-600 flex items-center justify-center font-bold text-xs">
                                                        {alpinista.nome.charAt(0).toUpperCase()}
                                                    </div>
                                                )}
                                                {alpinista.nome}
                                            </td>
                                            <td className="px-6 py-4 text-gray-500">
                                                {alpinista.email || "Não informado"}
                                            </td>
                                            <td className="px-6 py-4">
                                                {/* Como já filtramos, todos aqui serão amarelos (Pendente) */}
                                                <span className="px-3 py-1 rounded-full text-xs font-bold tracking-wide bg-yellow-100 text-yellow-700">
                                                    {(alpinista.status || 'pendente').toUpperCase()}
                                                </span>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* COLUNA DE AÇÕES RÁPIDAS */}
                <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 flex flex-col">
                    <h3 className="text-lg font-bold text-escalada-texto mb-4">Ações Rápidas</h3>
                    
                    <div className="flex flex-col gap-3 flex-1">
                        <Link href="/alpinistas" className="w-full py-3 px-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-sm font-medium text-escalada-texto transition-colors flex items-center gap-3">
                            <Plus size={18} className="text-escalada-azul" />
                            Adicionar Alpinista
                        </Link>
                        
                        <button className="w-full py-3 px-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-sm font-medium text-escalada-texto transition-colors flex items-center gap-3 cursor-not-allowed opacity-60">
                            <CalendarDays size={18} className="text-escalada-vermelho" />
                            Agendar Encontro
                        </button>
                    </div>
                    
                    <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-100">
                        <h4 className="text-sm font-bold text-escalada-azul mb-1">Dica de Gestão</h4>
                        <p className="text-xs text-blue-800">
                            Fique de olho na lista de "Inscrições Pendentes" para aprovar e ativar os novos membros rapidamente.
                        </p>
                    </div>
                </div>

            </div>
            
        </div>
    );
}