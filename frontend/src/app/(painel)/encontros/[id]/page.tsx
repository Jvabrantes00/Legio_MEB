"use client"

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { ArrowLeft, Users, Briefcase } from "lucide-react";
import { useParams } from "next/navigation";
import { siaFetch } from "../../../../lib/sia-api";
import { useSiaSession } from "../../../../components/SiaSessionProvider";
import { EncontroSummaryPanel } from "../../../../components/EncontroSummaryPanel";
import { ConfirmedAlpinistasTable } from "../../../../components/ConfirmedAlpinistasTable";
import { canManageEncontros, canViewEncontros } from "../../../../lib/sia-capabilities";
import {
    confirmedAlpinistas, isEncontroFull,
    type AlpinistaFull, type ConfirmedAlpinista, type EncounterParticipation,
    type EncontroFull, type EncontroSummary, type FuncaoEncontro,
} from "../../../../lib/sia-profile-contracts";
import {
    appendUniqueById,
    buildPaginatedPath,
    paginationControls,
    startPaginatedSearch,
    type PaginatedResponse,
} from "../../../../lib/integration-contracts";
import { errorMessage, readApiError } from "../../../../lib/form-api-error";

export default function DetalhesEncontro() {
    const { session, loading, error } = useSiaSession();
    if (loading) return <p className="p-10 text-gray-500">Carregando sessão...</p>;
    if (error) return <p className="p-10 text-red-600">{error}</p>;
    if (!canViewEncontros(session)) return <p className="p-10 text-gray-600">Seu papel não permite acessar Encontros.</p>;
    return canManageEncontros(session) ? <ManagedEncounterDetails /> : <EncounterSummaryDetails />;
}

function EncounterSummaryDetails() {
    const params = useParams<{ id: string }>();
    const encontroId = params.id;
    const [encontro, setEncontro] = useState<EncontroSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();
        async function load() {
            try {
                const response = await siaFetch(`/encontros/${encontroId}/`, { signal: controller.signal });
                if (!response.ok) throw new Error(await readApiError(response, "Não foi possível carregar o encontro."));
                const body: EncontroSummary = await response.json();
                if (!controller.signal.aborted) setEncontro(body);
            } catch (error: unknown) {
                if (!controller.signal.aborted) {
                    setEncontro(null);
                    setLoadError(errorMessage(error, "Não foi possível carregar o encontro."));
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }
        if (encontroId) void load();
        return () => controller.abort();
    }, [encontroId]);

    if (loading) return <p className="p-10 text-gray-500">Carregando resumo do encontro...</p>;
    if (loadError || !encontro) return <p className="p-10 text-red-600">{loadError || "Encontro indisponível."}</p>;
    return <div className="space-y-4">
        <Link href="/encontros" className="text-escalada-azul hover:underline">← Voltar aos encontros</Link>
        <EncontroSummaryPanel encontro={encontro} />
    </div>;
}

function ManagedEncounterDetails() {
    const params = useParams<{ id: string }>();
    const encontroId = params.id;

    const [encontro, setEncontro] = useState<EncontroFull | null>(null);
    const [carregando, setCarregando] = useState(true);

    const [abaAtiva, setAbaAtiva] = useState<"equipes" | "encontristas">("encontristas");

    const [modoLista, setModoLista] = useState<"pendentes" | "confirmados">("pendentes");

    const [pendentes, setPendentes] = useState<AlpinistaFull[]>([]);
    const [paginaPendentes, setPaginaPendentes] = useState(1);
    const [temMaisPendentes, setTemMaisPendentes] = useState(false);
    const [carregandoMaisPendentes, setCarregandoMaisPendentes] = useState(false);
    const [confirmados, setConfirmados] = useState<ConfirmedAlpinista[]>([]);
    const [selecionados, setSelecionados] = useState<number[]>([]);
    const [efetivando, setEfetivando] = useState(false);

    const buscarPendentes = useCallback(async (pagina = 1, acrescentar = false) => {
        try {
            if (acrescentar) setCarregandoMaisPendentes(true);
            const path = buildPaginatedPath(
                "/alpinistas/",
                { status: "pendente" },
                pagina,
            );
            const resposta = await siaFetch(path);
            if (!resposta.ok) throw new Error(await readApiError(resposta, "Erro ao buscar alpinistas pendentes."));
            {
                const dados: PaginatedResponse<AlpinistaFull> = await resposta.json();
                const controls = paginationControls(dados);
                setPendentes((atuais) => acrescentar
                    ? appendUniqueById(atuais, dados.results)
                    : dados.results
                );
                setPaginaPendentes(pagina);
                setTemMaisPendentes(controls.hasNext);
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Erro ao buscar alpinistas pendentes."));
        } finally {
            setCarregandoMaisPendentes(false);
        }
    }, []);

    const buscarConfirmados = useCallback(async () => {
        try {
            const resposta = await siaFetch(`/participacoes-encontros/?encontro=${encontroId}`);
            if (!resposta.ok) throw new Error(await readApiError(resposta, "Erro ao buscar alpinistas confirmados."));
            {
                const dados: PaginatedResponse<EncounterParticipation> = await resposta.json();
                setConfirmados(confirmedAlpinistas(dados.results));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Erro ao buscar alpinistas confirmados."));
        }
    }, [encontroId]);

    useEffect(() => {
        if (abaAtiva !== "encontristas") return;
        const timer = window.setTimeout(() => {
            void buscarPendentes();
            void buscarConfirmados();
            setSelecionados([]);
        }, 0);
        return () => window.clearTimeout(timer);
    }, [abaAtiva, buscarConfirmados, buscarPendentes]);

    const toggleSelecao = (id: number) => {
        if (selecionados.includes(id)) {
            setSelecionados(selecionados.filter((item) => item !== id));
        } else {
            setSelecionados([...selecionados, id]);
        }
    }

    const efetivarSelecionados = async () => {
        if (selecionados.length === 0) return toast.error("Selecione pelo menos um alpinista.");
        setEfetivando(true);
        try {
            const resposta = await siaFetch(`/encontros/${encontroId}/efetivar-encontristas/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify ({ alpinistas_ids: selecionados })
            });

            if (resposta.ok) {
                toast.success("Alpinistas confirmados no encontro!");
                setSelecionados([]);
                buscarPendentes();
                buscarConfirmados();
                setModoLista("confirmados");
            } else {
                toast.error(await readApiError(resposta, "Erro ao efetivar alpinistas."));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Falha de conexão."));
        } finally {
            setEfetivando(false);
        }
    };

    const alternarCoordenador = async (participacaoId: number, statusAtual: boolean) => {
        try {
            // Usamos PATCH porque queremos atualizar apenas um campo (coordenador)
            const resposta = await siaFetch(`/participacoes-encontros/${participacaoId}/`, {
                method: "PATCH", 
                headers: { 
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ coordenador: !statusAtual }) // Inverte o status atual
            });

            if (resposta.ok) {
                buscarEquipeTrabalho(); // Recarrega os cards para pintar a coroa
            } else {
                toast.error(await readApiError(resposta, "Erro ao atualizar coordenador."));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Falha de conexão."));
        }
    };


    const removerSelecionados = async () => {
        if (selecionados.length === 0) return toast.error("Selecione pelo menos um alpinista para remover.");
        setEfetivando(true); 
        try {
            const resposta = await siaFetch(`/encontros/${encontroId}/remover-encontristas/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify ({ alpinistas_ids: selecionados })
            });

            if (resposta.ok) {
                toast.success("Alpinistas removidos do encontro!");
                setSelecionados([]);
                buscarPendentes(); 
                buscarConfirmados(); 
            } else {
                toast.error(await readApiError(resposta, "Erro ao remover alpinistas."));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Falha de conexão."));
        } finally {
            setEfetivando(false);
        }
    };

    // ==========================================
    // ESTADOS: EQUIPES DE TRABALHO
    // ==========================================

    const [funcoes, setFuncoes] = useState<FuncaoEncontro[]>([]);
    const [equipeTrabalho, setEquipeTrabalho] = useState<EncounterParticipation[]>([]);

    const [isModalEquipeOpen, setIsModalEquipeOpen] = useState(false);
    const [funcaoAtual, setFuncaoAtual] = useState<FuncaoEncontro | null>(null);
    const [termoBusca, setTermoBusca] = useState("");
    const [resultadosBusca, setResultadosBusca] = useState<AlpinistaFull[]>([]);
    const [buscando, setBuscando] = useState(false);
    const [paginaBuscaEquipe, setPaginaBuscaEquipe] = useState(1);
    const [buscaTemAnterior, setBuscaTemAnterior] = useState(false);
    const [buscaTemProxima, setBuscaTemProxima] = useState(false);

    const buscarFuncoes = useCallback(async () => {
        try {
            const resposta = await siaFetch("/funcoes/");
            if (!resposta.ok) throw new Error(await readApiError(resposta, "Erro ao buscar funções."));
            {
                const dados: PaginatedResponse<FuncaoEncontro> = await resposta.json();
                setFuncoes(dados.results.filter((funcao) => funcao.tipo !== "encontrista"));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Erro ao buscar funções."));
        }
    }, []);

    const buscarEquipeTrabalho = useCallback(async () => {
        try {
            const resposta = await siaFetch(`/participacoes-encontros/?encontro=${encontroId}`);
            if (!resposta.ok) throw new Error(await readApiError(resposta, "Erro ao buscar equipe de trabalho."));
            {
                const dados: PaginatedResponse<EncounterParticipation> = await resposta.json();
                setEquipeTrabalho(dados.results.filter((participacao) => participacao.funcao.tipo !== "encontrista"));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Erro ao buscar equipe de trabalho."));
        }
    }, [encontroId]);

    useEffect(() => {
        if (abaAtiva !== "equipes") return;
        const timer = window.setTimeout(() => {
            void buscarFuncoes();
            void buscarEquipeTrabalho();
        }, 0);
        return () => window.clearTimeout(timer);
    }, [abaAtiva, buscarEquipeTrabalho, buscarFuncoes]);

    useEffect(() => {
        const delayDebouceFn = setTimeout(async () => {
            if(termoBusca.length >= 2){
                setBuscando(true);
                try {
                    const path = buildPaginatedPath(
                        "/alpinistas/",
                        { search: termoBusca, status: "ativo" },
                        paginaBuscaEquipe,
                    );
                    const resposta = await siaFetch(path);
                    if (!resposta.ok) throw new Error(await readApiError(resposta, "Erro na busca."));
                    {
                        const dados: PaginatedResponse<AlpinistaFull> = await resposta.json();
                        const controls = paginationControls(dados);
                        setResultadosBusca(dados.results);
                        setBuscaTemAnterior(controls.hasPrevious);
                        setBuscaTemProxima(controls.hasNext);
                    }
                } catch (error: unknown) {
                    toast.error(errorMessage(error, "Erro na busca."));
                } finally {
                    setBuscando(false);
                }
            } else {
                setResultadosBusca([]);
            }
        }, 500);
        
        return () => clearTimeout(delayDebouceFn);
    }, [termoBusca, paginaBuscaEquipe]);

    const adicionarNaEquipe = async (alpinistaId: number) => {
        if (!funcaoAtual) return;
        try {
            const payload = {
                encontro_id: encontroId,
                alpinista_id: alpinistaId,
                funcao_id: funcaoAtual.id
            };

            const resposta = await siaFetch("/participacoes-encontros/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(payload)
            });

            if(resposta.ok) {
                toast.success(`Alpinista adicionado à ${funcaoAtual.nome}!`);
                buscarEquipeTrabalho();
                setIsModalEquipeOpen(false);
                setTermoBusca("");
            } else {
                toast.error(await readApiError(resposta, "Erro ao adicionar na equipe."));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Falha de conexão."));
        }
    };

    const removerDaEquipe = async (participacaoId: number) => {
        if(!window.confirm("Remover este alpinista da equipe?")) return;
        try {
            const resposta = await siaFetch(`/participacoes-encontros/${participacaoId}/`, {
                method: "DELETE",
            });

            if (resposta.ok) {
                toast.success("Alpinista removido da equipe.");
                buscarEquipeTrabalho();
            } else {
                toast.error(await readApiError(resposta, "Erro ao remover da equipe."));
            }
        } catch (error: unknown) {
            toast.error(errorMessage(error, "Falha de conexão."));
        }
    };

    useEffect(() => {
        async function carregarDetalhes() {
            try {
                const resposta = await siaFetch(`/encontros/${encontroId}/`, {
                    method: "GET",
                });
                if (resposta.ok) {
                    const dados = await resposta.json();
                    if (isEncontroFull(dados)) setEncontro(dados);
                    else toast.error("Contrato do encontro completo indisponível.");
                } else {
                    toast.error(await readApiError(resposta, "Erro ao carregar detalhes do encontro."));
                }
            } catch (error: unknown) {
                toast.error(errorMessage(error, "Erro ao carregar detalhes do encontro."));
            } finally {
                setCarregando(false);
            }
        }

        if (encontroId) {
            carregarDetalhes();
        }
    }, [encontroId]);

    if (carregando) {
        return <div className="p-10 text-center font-medium text-gray-500">Carregando painel do encontro...</div>;
    }

    if (!encontro) {
        return ( 
        <div className="p-10 text-center">
            <p className="text-red-500 font-medium mb-4">Encontro não encontrado.</p>
            <Link href="/encontros" className="text-blue-600 hover:underline">Voltar para a lista de encontros</Link>
        </div>
        );
    }
    
    return (
        <div className="space-y-6">
            <div className = "flex items-center gap-4 mb-2">
                <Link href="/encontros" className="p-2 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors">
                    <ArrowLeft size={20} />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-gray-900">{encontro.encontro}</h1>
                    <p className="text-gray-500">Data: {new Date(encontro.data_referencia).toLocaleDateString('pt-BR', { timeZone: 'UTC' })} • Local: {encontro.local}</p>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-100 flex overflow-hidden">
                
                <button
                    onClick={() => setAbaAtiva("encontristas")}
                    className={`flex-1 py-4 flex items-center justify-center gap-2 border-l border-gray-100 font-semibold transition-colors ${abaAtiva === "encontristas" ? "bg-green-600 text-white" : "text-gray-600 hover:bg-gray-50"}`}
                >
                    <Users size={18} /> Encontristas
                </button>

                <button
                    onClick={() => setAbaAtiva("equipes")}
                    className={`flex-1 py-4 flex items-center justify-center gap-2 border-l border-gray-100 font-semibold transition-colors ${abaAtiva === "equipes" ? "bg-escalada-vermelho text-white" : "text-gray-600 hover:bg-gray-50"}`}
                >
                    <Briefcase size={18} /> Equipes de Trabalho
                </button>

            </div>

            <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 min-h-[400px]">
                {abaAtiva === "equipes" && (
                    <div className="animate-in fade-in duration-300 relative">
                        
                        {/* CABEÇALHO DA ABA E BOTÃO DA MATRIZ */}
                        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 border-b pb-4 gap-4">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Montagem das Equipes</h2>
                                <p className="text-sm text-gray-500 mt-1">Pré-selecione os alpinistas para cada função deste encontro.</p>
                            </div>
                            
                        </div>

                        {/* GRID DOS CARDS DE FUNÇÃO (Opção B) */}
                        {funcoes.length === 0 ? (
                            <div className="text-center p-10 text-gray-500 bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                Nenhuma função de trabalho cadastrada no sistema. (Ex: Cozinha, Apoio).
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                {funcoes.map((funcao) => {
                                    // Filtra os trabalhadores específicos deste card
                                    const trabalhadores = equipeTrabalho.filter(p => p.funcao?.id === funcao.id);
                                    
                                    return (
                                        <div key={funcao.id} className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex flex-col">
                                            {/* Cabeçalho do Card */}
                                            <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex justify-between items-center">
                                                <h3 className="font-bold text-gray-800">{funcao.nome}</h3>
                                                <span className="bg-gray-200 text-gray-700 text-xs font-bold px-2 py-1 rounded-full">
                                                    {trabalhadores.length}
                                                </span>
                                            </div>
                                            
                                            {/* Lista de Membros */}
                                            <div className="p-4 flex-1">
                                                {trabalhadores.length === 0 ? (
                                                    <p className="text-sm text-gray-400 text-center py-4">Equipe vazia</p>
                                                ) : (
                                                    <ul className="space-y-3">
                                                        {trabalhadores.map((trab) => (
                                                            <li key={trab.id} className="flex justify-between items-center group p-1 -mx-1 hover:bg-gray-50 rounded transition-colors">
                                                                <div className="flex items-center gap-2">
                                                                    {/* BOTÃO DA COROA */}
                                                                    <button
                                                                        onClick={() => alternarCoordenador(trab.id, trab.coordenador)}
                                                                        className={`transition-all duration-200 ${trab.coordenador ? 'opacity-100 grayscale-0 scale-110' : 'opacity-0 grayscale group-hover:opacity-100 hover:grayscale-0'}`}
                                                                        title={trab.coordenador ? "Remover Coordenação" : "Tornar Coordenador"}
                                                                    >
                                                                        👣
                                                                    </button>
                                                                    
                                                                    {/* NOME DO ALPINISTA (Muda de cor se for coordenador) */}
                                                                    <span className={`text-sm ${trab.coordenador ? 'font-bold text-escalada-azul' : 'font-semibold text-gray-800'}`}>
                                                                        {trab.alpinista?.nome}
                                                                    </span>
                                                                </div>
                                                                
                                                                {/* BOTÃO DE REMOVER (X) */}
                                                                <button 
                                                                    onClick={() => removerDaEquipe(trab.id)}
                                                                    className="text-red-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                                                                    title="Remover da Equipe"
                                                                >
                                                                    ✕
                                                                </button>
                                                            </li>
                                                        ))}
                                                    </ul>
                                                )}
                                            </div>
                                            
                                            {/* Botão de Adicionar no Rodapé do Card */}
                                            <div className="p-3 border-t border-gray-100 bg-gray-50/50">
                                                <button 
                                                    onClick={() => {
                                                        setFuncaoAtual(funcao);
                                                        setTermoBusca("");
                                                        setResultadosBusca([]);
                                                        setPaginaBuscaEquipe(1);
                                                        setBuscaTemAnterior(false);
                                                        setBuscaTemProxima(false);
                                                        setIsModalEquipeOpen(true);
                                                    }}
                                                    className="w-full py-2 text-sm font-semibold text-escalada-azul hover:bg-blue-50 rounded-lg transition-colors flex items-center justify-center gap-1"
                                                >
                                                    + Adicionar Membro
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* ========================================== */}
                        {/* MODAL DE BUSCA RÁPIDA DE ALPINISTAS        */}
                        {/* ========================================== */}
                        {isModalEquipeOpen && (
                            <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
                                <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-2xl relative">
                                    <button 
                                        onClick={() => setIsModalEquipeOpen(false)}
                                        className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
                                    >✕</button>
                                    
                                    <h2 className="text-xl font-bold text-gray-800 mb-1">Escalar para: {funcaoAtual?.nome}</h2>
                                    <p className="text-sm text-gray-500 mb-5">Busque pelo nome do alpinista (apenas ativos).</p>
                                    
                                    <div className="relative mb-4">
                                        <input 
                                            type="text" 
                                            placeholder="Digite o nome..." 
                                            value={termoBusca}
                                            onChange={(e) => {
                                                const next = startPaginatedSearch(e.target.value);
                                                setTermoBusca(next.search);
                                                setPaginaBuscaEquipe(next.page);
                                            }}
                                            className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-escalada-azul focus:outline-none"
                                            autoFocus
                                        />
                                        {buscando && <span className="absolute right-4 top-3.5 text-sm text-gray-400">Buscando...</span>}
                                    </div>

                                    <div className="max-h-60 overflow-y-auto border border-gray-100 rounded-lg">
                                        {termoBusca.length > 0 && resultadosBusca.length === 0 && !buscando && (
                                            <p className="p-4 text-center text-sm text-gray-500">Nenhum alpinista ativo encontrado.</p>
                                        )}
                                        {resultadosBusca.map(alp => (
                                            <div key={alp.id} className="flex justify-between items-center p-3 hover:bg-gray-50 border-b border-gray-50 last:border-0">
                                                <span className="font-medium text-sm text-gray-800">{alp.nome}</span>
                                                <button 
                                                    onClick={() => adicionarNaEquipe(alp.id)}
                                                    className="px-3 py-1 bg-escalada-azul text-white text-xs font-bold rounded hover:bg-blue-800 transition-colors"
                                                >
                                                    Adicionar
                                                </button>
                                            </div>
                                        ))}
                                        {termoBusca.length >= 2 && (buscaTemAnterior || buscaTemProxima) && (
                                            <div className="sticky bottom-0 flex items-center justify-between gap-2 border-t border-gray-100 bg-white p-3">
                                                <button
                                                    type="button"
                                                    onClick={() => setPaginaBuscaEquipe((pagina) => pagina - 1)}
                                                    disabled={!buscaTemAnterior || buscando}
                                                    className="px-3 py-1 text-xs font-semibold border rounded disabled:opacity-50"
                                                >
                                                    Anterior
                                                </button>
                                                <span className="text-xs text-gray-500">Página {paginaBuscaEquipe}</span>
                                                <button
                                                    type="button"
                                                    onClick={() => setPaginaBuscaEquipe((pagina) => pagina + 1)}
                                                    disabled={!buscaTemProxima || buscando}
                                                    className="px-3 py-1 text-xs font-semibold border rounded disabled:opacity-50"
                                                >
                                                    Próxima
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {abaAtiva === "encontristas" && (
                    <div className="animate-in fade-in duration-300">
                        <div className="flex justify-between items-center mb-6 border-b pb-4">
                            <div>
                                <h2 className="text-xl font-bold text-gray-800">Inscrições Pendentes</h2>
                                <p className="text-sm text-gray-500 mt-1">Selecione os jovens que confirmaram presença no encontro.</p>
                            </div>

                            <div className="flex gap-2">
                                <button
                                    onClick={() => { setModoLista("pendentes"); setSelecionados([]); }}
                                    className={`px-4 py-2 rounded-lg font-bold transition-colors shadow-sm ${modoLista === "pendentes" ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                                >   
                                    Fila de Espera
                                </button>
                                <button
                                    onClick={() => { setModoLista("confirmados"); setSelecionados([]); }}
                                    className={`px-4 py-2 rounded-lg font-bold transition-colors shadow-sm ${modoLista === "confirmados" ? "bg-gray-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}
                                >
                                    Confirmados ({confirmados.length})
                                </button>
                            </div>
                        </div>

                        {modoLista === "pendentes" && (
                            <>
                                <div className="flex justify-end mb-4">
                                    <button
                                        onClick={efetivarSelecionados}
                                        disabled={selecionados.length === 0 || efetivando}
                                        className="px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-bold transition-colors disabled:opacity-100 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                                    >
                                        {efetivando ? "Processando..." : `Confirmar Selecionados (${selecionados.length})`}
                                    </button>
                                </div>

                                {pendentes.length === 0 ? (
                                    <div className="p-10 text-center bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                        <p className="text-gray-500">Não há inscrições pendentes.</p>
                                    </div>
                                ) : (
                                    <div className="overflow-x-auto border border-gray-200 rounded-xl">
                                        <table className="w-full text-left">
                                            <thead className="bg-gray-50 border-b border-gray-200 text-sm text-gray-500 uppercase">
                                                <tr>
                                                    <th className="px-4 py-3 w-10 text-center"> <Users size={16} className="mx-auto" /> </th>
                                                    <th className="px-4 py-3 font-semibold">Nome</th>
                                                    <th className="px-4 py-3 font-semibold">Contato</th>
                                                    <th className="px-6 py-3 font-semibold">Idade / Nasc</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100">
                                                {pendentes.map((alpinista) => (
                                                    <tr key={alpinista.id} className="hover:bg-green-50/50 transition-colors cursor-pointer" onClick={() => toggleSelecao(alpinista.id)}>
                                                        <td className="px-4 py-4 text-center">
                                                            <input 
                                                                type="checkbox"
                                                                checked={selecionados.includes(alpinista.id)}
                                                                onChange={() => toggleSelecao(alpinista.id)}
                                                                className="w-5 h-5 text-green-600 rounded border-gray-300 focus:ring-green-500 cursor-pointer"
                                                                onClick={ (e) => e.stopPropagation() }
                                                            />
                                                        </td>
                                                        <td className="px-4 py-4 font-medium text-gray-900">{alpinista.nome}</td>
                                                        <td className="px-4 py-4 text-sm text-gray-600">
                                                            {alpinista.telefone} <br />
                                                            <span className="text-xs text-gray-400">{alpinista.email}</span>
                                                        </td>
                                                        <td className="px-4 py-4 text-sm text-gray-600">
                                                            {alpinista.dataNascimento || "-"}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
                                {temMaisPendentes && (
                                    <div className="mt-4 flex justify-center">
                                        <button
                                            type="button"
                                            onClick={() => buscarPendentes(paginaPendentes + 1, true)}
                                            disabled={carregandoMaisPendentes}
                                            className="px-4 py-2 text-sm font-semibold border border-gray-200 rounded-lg disabled:opacity-50"
                                        >
                                            {carregandoMaisPendentes ? "Carregando..." : "Carregar mais pendentes"}
                                        </button>
                                    </div>
                                )}
                            </>
                        )}

                        {modoLista === "confirmados" && (
                            <div className="animate-in fade-in duration-300">
                                <div className="flex justify-end mb-4">
                                    <button 
                                        onClick={removerSelecionados}
                                        disabled={selecionados.length === 0 || efetivando}
                                        className="px-6 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                                    >
                                        {efetivando ? "Processando..." : `Remover Selecionados (${selecionados.length})`}
                                    </button>
                                </div>

                                {confirmados.length === 0 ? (
                                    <div className="p-10 text-center bg-gray-50 rounded-xl border border-dashed border-gray-200">
                                        <p className="text-gray-500">Nenhum alpinista pré-selecionado para este encontro ainda.</p>
                                    </div>
                                ) : (
                                    <ConfirmedAlpinistasTable people={confirmados} selected={selecionados} toggle={toggleSelecao} />
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )}
