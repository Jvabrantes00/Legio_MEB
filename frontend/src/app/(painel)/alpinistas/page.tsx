"use client";

// ============================================================================
// IMPORTAÇÕES
// ============================================================================
import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Plus, Search, MoreHorizontal, X, Pencil, Trash2, Filter, ChevronLeft, ChevronRight, Calendar, Briefcase, Camera, Key, Maximize2, Ticket, ArrowUpDown  } from "lucide-react";

// ============================================================================
// INTERFACE (CONTRATO DE DADOS)
// ============================================================================
interface EncontroRealizado {
    tipo: string;
    nome_encontro: string;
    data: string | null;
    cor_grupo?: string | null;
}

interface HistoricoEquipe {
    nome_encontro: string;
    equipe: string;
    tipo_encontro: string;
    data: string | null;
    cor_grupo?: string | null;
}

interface HistoricoEvento {
    nome_evento: string;
    data: string | null;
}

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

    is_neurodivergente?: boolean;
    tipo_neurodivergente?: string;

    encontros_realizados?: EncontroRealizado[];
    historico_eventos?: HistoricoEvento[];
    historico_equipes?: HistoricoEquipe[];
}

export default function AlpinistasPage() {
    
    // ============================================================================
    // ESTADOS GERAIS E FILTROS DA LISTA
    // ============================================================================

    const [isMounted, setIsMounted] = useState(false);

    useEffect(() => {
        setIsMounted(true);
    }, []);

    const [alpinistas, setAlpinistas] = useState<Alpinista[]>([]);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");

    const [nextPageUrl, setNextPageUrl] = useState<string | null>(null);
    const [prevPageUrl, setPrevPageUrl] = useState<string | null>(null);
    const [totalAlpinistas, setTotalAlpinistas] = useState(0);
    
    // FILTROS
    const [busca, setBusca] = useState(""); // Filtro de Texto (Nome, Email, Tel)
    const [filtroStatus, setFiltroStatus] = useState("TODOS"); // NOVO: Filtro Avançado de Status
    const [filtroOrdem, setFiltroOrdem] = useState("A-Z")

    // ============================================================================
    // ESTADO: CONTROLE DO MENU DROPDOWN (TRÊS PONTINHOS)
    // ============================================================================
    const [menuAberto, setMenuAberto] = useState<number | null>(null);

    // ============================================================================
    // ESTADOS DO MODAL DE FORMULÁRIO (CREATE E UPDATE)
    // ============================================================================
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [salvando, setSalvando] = useState(false);
    const [idEdicao, setIdEdicao] = useState<number | null>(null);
    const [fotoArquivo, setFotoArquivo] = useState<File | null>(null)

    const [formData, setFormData] = useState({
        nome: '', email: '', telefone: '', dataNascimento: '',
        endereco: '', nomePai: '', telefonePai: '', nomeMae: '',
        telefoneMae: '', restricaoSaude: '', medicacao: '',
        grupo: '', status: 'ativo', is_neurodivergente: false, tipo_neurodivergente: ''
    });

    // ============================================================================
    // ESTADOS DA FICHA DETALHADA (READ) E EXCLUSÃO (DELETE)
    // ============================================================================
    const [isFichaOpen, setIsFichaOpen] = useState(false);
    const [alpinistaSelecionado, setAlpinistaSelecionado] = useState<Alpinista | null>(null);

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [alpinistaParaDeletar, setAlpinistaParaDeletar] = useState<Alpinista | null>(null);
    const [deletando, setDeletando] = useState(false);

    const [isHistoricoGeralOpen, setIsHistoricoGeralOpen] = useState(false);
    const [abaHistorico, setAbaHistorico] = useState<'encontros' | 'equipe' | 'eventos'>('encontros');

    // ============================================================================
    // INTEGRAÇÃO COM A API (DEBOUCE)
    // ============================================================================
    const getCookie = (nome: string) => {
        if(typeof document === 'undefined') return null;
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; ${nome}=`);
        if (partes.length === 2) return partes.pop()?.split(';').shift();
        return null;
    };

    const buscarAlpinistas = async (url: string = "https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/") => {
        try {
            setCarregando(true);
            const token = getCookie('sia_token');
            if (!token) throw new Error("Token de autenticação não encontrado.");

            let urlCorrigida = url;
            if(url.includes('127.0.0.1') || url.includes( 'localhost')){
                const urlObj = new URL(url);
                urlCorrigida = `https://wpc8m7lx-8000.brs.devtunnels.ms${urlObj.pathname}${urlObj.search}`;

            }
            urlCorrigida = urlCorrigida + ( urlCorrigida.includes('?') ? '&' : '?') + 't=' + new Date().getTime();

            const resposta = await fetch(urlCorrigida, {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                cache: 'no-store'
            });

            if (!resposta.ok) throw new Error("Não foi possível carregar a lista de alpinistas.");

            const dados = await resposta.json();
            setAlpinistas(dados.results || []);
            setNextPageUrl(dados.next || null);
            setPrevPageUrl(dados.previous || null);

            setTotalAlpinistas(dados.count || 0);

        } catch (error: any) {
            setErro(error.message);
        } finally {
            setCarregando(false);
        }
    };

    useEffect(()=> {
        const timer = setTimeout(() => {
            const baseUrl = "https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/";
            const url = busca.trim() !== ""
                ? `${ baseUrl}?search=${encodeURIComponent(busca)}`
                : baseUrl;
        
            buscarAlpinistas(url);
        }, 500);
        return () => clearTimeout(timer);
    }, [busca]);

    const irParaPrimeiraPagina = () => {
        const baseUrl = "https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/";
        const url = busca.trim() !==""
            ? `${ baseUrl}?search=${encodeURIComponent(busca)}`
            : baseUrl;
        buscarAlpinistas(url);
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const target = e.target as HTMLInputElement;
        const { name, value, type, checked } = target;
        setFormData(prev => ({ ...prev, 
            [name]: type === 'checkbox' ? checked : value }));
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if(e.target.files && e.target.files.length > 0) setFotoArquivo(e.target.files[0]);
    }

    const salvarAlpinista = async (e: React.FormEvent) => {
        e.preventDefault(); 
        setSalvando(true);

        try {
            const token = getCookie('sia_token');
            const formDataToSend = new FormData();

            Object.entries(formData).forEach(([key, value]) => {
                if (key === 'tipo_neurodivergente' && !formData.is_neurodivergente) {
                    return;
                }

                if (value !== '' && value !== null) {
                    formDataToSend.append(key, value as string);
                }
            });

            if (fotoArquivo) {
                formDataToSend.append( 'foto', fotoArquivo);
            }

            const url = idEdicao 
                ? `https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/${idEdicao}/` 
                : "https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/";
            
            const metodo = idEdicao ? "PUT" : "POST";

            const resposta = await fetch(url, {
                method: metodo,
                headers: {
                    "Authorization": `Bearer ${token}` 
                },
                body: formDataToSend
            });

            if (!resposta.ok) throw new Error("Erro ao salvar. Verifique os dados e tente novamente.");

            setIsModalOpen(false); 
            buscarAlpinistas("https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/");    

        } catch (error: any) {
            alert(error.message);
        } finally {
            setSalvando(false);
        }
    };

    const executarDelecao = async () => {
        if (!alpinistaParaDeletar) return;
        setDeletando(true);

        try {
            const token = getCookie('sia_token');
            const resposta = await fetch(`https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/${alpinistaParaDeletar.id}/`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}` 
                }
            });

            if (!resposta.ok) throw new Error("Não foi possível excluir o alpinista.");

            setIsDeleteModalOpen(false);
            setAlpinistaParaDeletar(null);

            const baseUrl = "https://wpc8m7lx-8000.brs.devtunnels.ms/api/alpinistas/";
            const url = busca.trim() !== ""
                ? `${ baseUrl}?search=${encodeURIComponent(busca)}`
                : baseUrl;
            buscarAlpinistas(url);

        } catch (error: any) {
            alert(error.message);
        } finally {
            setDeletando(false);
        }
    };

    // ============================================================================
    // CONTROLES DE ABERTURA DE MODAIS E MENUS
    // ============================================================================
    const alternarMenu = (e: React.MouseEvent, id: number) => {
        e.stopPropagation(); 
        setMenuAberto(prev => (prev === id ? null : id));
    };

    const abrirModalNovo = () => {
        setIdEdicao(null); 
        setFormData({
            nome: '', email: '', telefone: '', dataNascimento: '',
            endereco: '', nomePai: '', telefonePai: '', nomeMae: '',
            telefoneMae: '', restricaoSaude: '', medicacao: '',
            grupo: '', status: 'ativo', is_neurodivergente: false, tipo_neurodivergente: ''
        });
        setIsModalOpen(true);
    };

    const abrirModalEdicao = (alpinista: Alpinista) => {
        setIdEdicao(alpinista.id); 
        setFormData({
            nome: alpinista.nome || '', email: alpinista.email || '', telefone: alpinista.telefone || '', 
            dataNascimento: alpinista.dataNascimento || '', endereco: alpinista.endereco || '', 
            nomePai: alpinista.nomePai || '', telefonePai: alpinista.telefonePai || '', 
            nomeMae: alpinista.nomeMae || '', telefoneMae: alpinista.telefoneMae || '', 
            restricaoSaude: alpinista.restricaoSaude || '', medicacao: alpinista.medicacao || '',
            grupo: alpinista.grupo || '', status: alpinista.status || 'ativo', is_neurodivergente: alpinista.is_neurodivergente || false, tipo_neurodivergente: alpinista.tipo_neurodivergente || ''
        });
        
        setIsFichaOpen(false); 
        setMenuAberto(null); 
        setIsModalOpen(true);  
    };

    const abrirFicha = (alpinista: Alpinista) => {
        setAlpinistaSelecionado(alpinista);
        setIsFichaOpen(true);
    };

    const confirmarDelecao = (alpinista: Alpinista) => {
        setAlpinistaParaDeletar(alpinista);
        setMenuAberto(null); 
        setIsDeleteModalOpen(true); 
    };

    const alpinistasFiltrados = alpinistas
        .filter((alpinista) => {
            return filtroStatus === "TODOS" || (alpinista.status || 'ativo').toLowerCase() === filtroStatus.toLowerCase();
    })
        .sort((a,b) =>{
            if (filtroOrdem === "A-Z") {
                return a.nome.localeCompare(b.nome);
            } else if (filtroOrdem === "Z=A") {
                return b.nome.localeCompare(a.nome);
            }
            return 0;
        });

   
    const encontrosSeguros = alpinistaSelecionado?.encontros_realizados || [];
    const equipesSeguras = alpinistaSelecionado?.historico_equipes || [];
    const eventosSeguros = alpinistaSelecionado?.historico_eventos || [];

    // ============================================================================
    // RENDERIZAÇÃO DA INTERFACE (JSX / HTML)
    // ============================================================================
    return (
        <div className="space-y-6 relative">
            
            {/* CABEÇALHO */}
            <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800">Alpinistas</h1>
                    <p className="text-sm text-gray-500 mt-1">Gerencie os membros do Movimento Escalada.</p>
                </div>
                <button 
                    onClick={abrirModalNovo}
                    className="bg-escalada-azul hover:bg-blue-800 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors shadow-sm"
                >
                    <Plus size={20} />
                    Novo Alpinista
                </button>
            </div>

            {/* ÁREA DE FILTROS E BUSCA AVANÇADA */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4">
                
                {/* Filtro de Texto (Esquerda) */}
                <div className="flex-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input 
                        type="text" 
                        placeholder="Buscar por nome, email ou telefone..." 
                        value={busca} 
                        onChange={(e) => setBusca(e.target.value)} 
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul transition-all"
                    />
                </div>

                {/* NOVO: Filtro Avançado de Status (Direita) */}
                <div className="relative md:w-64">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Filter className="h-4 w-4 text-gray-400" />
                    </div>
                    {/* Select que atualiza o estado 'filtroStatus' dinamicamente */}
                    <select 
                        value={filtroStatus}
                        onChange={(e) => setFiltroStatus(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul transition-all appearance-none cursor-pointer font-medium"
                    >
                        <option value="TODOS">Todos os Status</option>
                        <option value="ativo">Ativos</option>
                        <option value="inativo">Inativos</option>
                        <option value="pendente">Pendentes</option>
                    </select>
                    {/* Setinha customizada para o Select */}
                    <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                    </div>
                </div>

                <div className="relative w-full md:w-48">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <ArrowUpDown className="h-4 w-4 text-gray-400" />
                        </div>
                        <select 
                            value={filtroOrdem}
                            onChange={(e) => setFiltroOrdem(e.target.value)}
                            className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 focus:outline-none focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul transition-all appearance-none cursor-pointer font-medium"
                        >
                            <option value="A-Z">Ordem: A - Z</option>
                            <option value="Z-A">Ordem: Z - A</option>
                            <option value="PADRAO">Mais Recentes</option>
                        </select>
                        <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none">
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
                        </div>
                    </div>

            </div>

            {/* ÁREA DA TABELA DE DADOS */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden relative">
                {menuAberto !== null && <div className="fixed inset-0 z-[9999]" onClick={() => setMenuAberto(null)}></div>}
                {carregando && <div className="p-10 text-center text-gray-500 font-medium">Carregando dados do banco...</div>}
                {erro && <div className="p-10 text-center text-red-500 font-medium bg-red-50">{erro}</div>}

                {!carregando && !erro && alpinistas.length === 0 && <div className="p-10 text-center text-gray-500">Nenhum alpinista cadastrado.</div>}
                
                {/* Mensagem atualizada para avisar que a busca (texto OU status) não achou nada */}
                {!carregando && !erro && alpinistas.length > 0 && alpinistasFiltrados.length === 0 && (
                    <div className="p-10 text-center text-gray-500">
                        Nenhum alpinista encontrado com os filtros selecionados.
                    </div>
                )}

                {!carregando && !erro && alpinistasFiltrados.length > 0 && (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-100 text-sm text-gray-500 uppercase tracking-wider">
                                    <th className="px-6 py-4 font-medium">Nome</th>
                                    <th className="px-6 py-4 font-medium">E-mail</th>
                                    {/* Adicionamos a coluna Status visualmente na tabela para fazer sentido com o filtro */}
                                    <th className="px-6 py-4 font-medium">Status</th>
                                    <th className="px-6 py-4 font-medium text-right">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {alpinistasFiltrados.map((alpinista) => (
                                    <tr 
                                        key={alpinista.id} 
                                        onClick={() => abrirFicha(alpinista)} 
                                        className="hover:bg-gray-50 transition-colors cursor-pointer"
                                    >
                                        <td className="px-6 py-6 flex items-center gap-4">
                                            {alpinista.foto ? (
                                                <img src={alpinista.foto} alt="Foto" className="w-12 h-12 rounded-full object-cover border border-gray-200" />
                                            ) : (
                                                <div className="w-12 h-12 rounded-full bg-blue-50 text-escalada-azul flex items-center justify-center font-bold text-sm border border-blue-100">
                                                    {alpinista.nome.charAt(0).toUpperCase()}
                                                </div>
                                            )}
                                            <span className="text-base font-medium text-gray-900">{alpinista.nome}</span>
                                        </td>
                                        
                                        <td className="px-6 py-6 text-sm text-gray-500">{alpinista.email || "Não informado"}</td>
                                        
                                        {/* NOVA: Célula de Status com cor dependendo do estado */}
                                        <td className="px-6 py-6">
                                            <span className={`px-3 py-1 rounded-full text-xs font-medium 
                                                ${(alpinista.status || '').toLowerCase() === 'ativo' ? 'bg-green-100 text-green-700' : 
                                                  (alpinista.status || '').toLowerCase() === 'inativo' ? 'bg-gray-100 text-gray-700' : 
                                                  'bg-yellow-100 text-yellow-700'}`}
                                            >
                                                {(alpinista.status || 'ativo').toUpperCase()}
                                            </span>
                                        </td>
                                        
                                        <td className="px-6 py-6 text-sm text-right relative">
                                            <button 
                                                onClick={(e) => alternarMenu(e, alpinista.id)} 
                                                className={`transition-colors p-2 rounded-lg relative z-20 ${menuAberto === alpinista.id ? 'bg-blue-100 text-escalada-azul' : 'text-gray-400 hover:bg-blue-50 hover:text-escalada-azul'}`}
                                            >
                                                <MoreHorizontal size={24} />
                                            </button>

                                            {menuAberto === alpinista.id && (
                                                <div 
                                                    className="absolute right-6 top-14 w-40 bg-white rounded-lg shadow-xl border border-gray-100 z-30 py-2 flex flex-col"
                                                    onClick={(e) => e.stopPropagation()} 
                                                >
                                                    <button 
                                                        onClick={(e) => { e.stopPropagation(); abrirModalEdicao(alpinista); }} 
                                                        className="w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-escalada-azul flex items-center gap-2 transition-colors"
                                                    >
                                                        <Pencil size={16} /> Editar
                                                    </button>
                                                    
                                                    <button 
                                                        onClick={(e) => { e.stopPropagation(); confirmarDelecao(alpinista); }} 
                                                        className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2 transition-colors"
                                                    >
                                                        <Trash2 size={16} /> Excluir
                                                    </button>
                                                </div>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                { !carregando && !erro && totalAlpinistas > 0 && (
                                <div className="felx items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50">
                                    <span className="text-sm text-gray-500">
                                        Total no banco: <span className="font-bold text-escalada-texto">{totalAlpinistas}</span>
                                    </span>
                                    <div className="flex gap-2">

                                        <button
                                            onClick={irParaPrimeiraPagina}
                                            disabled={!prevPageUrl}
                                            title="Voltar para a primeira página"
                                            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm">
                                            <ChevronLeft size={16} />

                                        </button>


                                        <button
                                            onClick={() => prevPageUrl && buscarAlpinistas(prevPageUrl)}
                                            disabled={!prevPageUrl}
                                            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-70 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm">
                                            <ChevronLeft size={16} />
                                            Anterior
                                        </button>
                                        <button
                                            onClick={() => nextPageUrl && buscarAlpinistas(nextPageUrl)}
                                            disabled={!nextPageUrl}
                                            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-70 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm">
                                            Próximo
                                            <ChevronRight size={16} />
                                        </button>
                                    </div>
                                </div>
                            )}
            </div>

            {/* ============================================================================ */}
            {/* MODAIS (CREATE, UPDATE, READ, DELETE) FICAM ABAIXO INTACTOS                  */}
            {/* ============================================================================ */}
            
            {/* Modal de Formulário (Criar/Editar) */}
            {isMounted && isModalOpen && createPortal (
                <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
                        <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-white">
                            <h2 className="text-xl font-bold text-gray-800">
                                {idEdicao ? "Editar Alpinista" : "Cadastrar Novo Alpinista"}
                            </h2>
                            <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition-colors">
                                <X size={24} />
                            </button>
                        </div>
                        <div className="overflow-y-auto p-6 flex-1">
                            <form id="form-alpinista" onSubmit={salvarAlpinista} className="space-y-6">
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Dados Pessoais</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-1">Nome Completo *</label><input type="text" name="nome" required value={formData.nome} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label><input type="email" name="email" value={formData.email} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label><input type="tel" name="telefone" value={formData.telefone} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento</label><input type="date" name="dataNascimento" value={formData.dataNascimento} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label><input type="text" name="endereco" value={formData.endereco} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Filiação</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Nome do Pai/Resp</label><input type="text" name="nomePai" value={formData.nomePai} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Telefone do Pai/Resp</label><input type="tel" name="telefonePai" value={formData.telefonePai} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Nome da Mãe/Resp</label><input type="text" name="nomeMae" value={formData.nomeMae} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Telefone da Mãe/Resp</label><input type="tel" name="telefoneMae" value={formData.telefoneMae} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                    </div>
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Saúde e Institucional</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-1">Restrições de Saúde</label><input type="text" name="restricaoSaude" value={formData.restricaoSaude} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" placeholder="Alergias, condições, etc." /></div>
                                        <div className="md:col-span-2"><label className="block text-sm font-medium text-gray-700 mb-1">Medicações em Uso</label><input type="text" name="medicacao" value={formData.medicacao} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div><label className="block text-sm font-medium text-gray-700 mb-1">Grupo</label><input type="text" name="grupo" value={formData.grupo} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" /></div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                                            <select name="status" value={formData.status} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul bg-white">
                                                <option value="ativo">Ativo</option>
                                                <option value="inativo">Inativo</option>
                                                <option value="pendente">Pendente</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>
                        <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 rounded-b-2xl">
                            <button type="button" onClick={() => setIsModalOpen(false)} className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors shadow-sm">Cancelar</button>
                            <button type="submit" form="form-alpinista" disabled={salvando} className="px-5 py-2.5 text-sm font-medium text-white bg-escalada-azul hover:bg-blue-800 rounded-lg transition-colors shadow-sm disabled:opacity-50">
                                {salvando ? "Salvando..." : (idEdicao ? "Salvar Alterações" : "Salvar Alpinista")}
                            </button>
                        </div>
                    </div>
                </div>,
                document.body
            )}

            {/* Modal de Leitura Detalhada (Ficha) */}
            {isMounted && isFichaOpen && alpinistaSelecionado && createPortal (
                <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
                        <div className="flex justify-between items-start p-6 border-b border-gray-100 bg-escalada-azul text-white relative">
                            <div className="flex items-center gap-4">
                                {alpinistaSelecionado.foto ? (
                                    <img src={alpinistaSelecionado.foto} alt="Foto" className="w-16 h-16 rounded-full object-cover border-2 border-white shadow-md" />
                                ) : (
                                    <div className="w-16 h-16 rounded-full bg-white text-escalada-azul flex items-center justify-center font-bold text-2xl shadow-md">
                                        {alpinistaSelecionado.nome.charAt(0).toUpperCase()}
                                    </div>
                                )}
                                <div>
                                    <h2 className="text-2xl font-bold">{alpinistaSelecionado.nome}</h2>
                                    <span className="inline-block px-3 py-1 bg-white/20 rounded-full text-xs font-medium mt-2">Status: {alpinistaSelecionado.status.toUpperCase()}</span>
                                </div>
                            </div>
                            <div className="flex gap-2">
                                <button onClick={() => abrirModalEdicao(alpinistaSelecionado)} className="flex items-center gap-2 bg-white/20 hover:bg-white/30 text-white px-3 py-2 rounded-lg text-sm font-medium transition-colors"><Pencil size={16} />Editar</button>
                                <button onClick={() => setIsFichaOpen(false)} className="text-blue-200 hover:text-white transition-colors bg-white/10 p-2 rounded-full h-fit"><X size={24} /></button>
                            </div>
                        </div>


                        <div className="overflow-y-auto p-6 flex-1 bg-gray-50">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                                
                                {/* COLUNA 1: DADOS PESSOAIS */}
                                <div className="lg:col-span-2 space-y-6">
                                    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
                                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">Contato e Dados Pessoais</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-6">
                                            <div><p className="text-xs text-gray-500 mb-1">E-mail</p><p className="font-medium text-gray-900">{alpinistaSelecionado.email || "Não informado"}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Telefone</p><p className="font-medium text-gray-900">{alpinistaSelecionado.telefone || "Não informado"}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Data de Nascimento</p><p className="font-medium text-gray-900">{alpinistaSelecionado.dataNascimento || "Não informada"}</p></div>
                                            <div className="md:col-span-2"><p className="text-xs text-gray-500 mb-1">Endereço</p><p className="font-medium text-gray-900">{alpinistaSelecionado.endereco || "Não informado"}</p></div>
                                        </div>
                                    </div>
                                    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
                                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">Filiação</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-6">
                                            <div><p className="text-xs text-gray-500 mb-1">Nome do Pai/Resp</p><p className="font-medium text-gray-900">{alpinistaSelecionado.nomePai || "Não informado"}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Telefone do Pai/Resp</p><p className="font-medium text-gray-900">{alpinistaSelecionado.telefonePai || "Não informado"}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Nome da Mãe/Resp</p><p className="font-medium text-gray-900">{alpinistaSelecionado.nomeMae || "Não informado"}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Telefone da Mãe/Resp</p><p className="font-medium text-gray-900">{alpinistaSelecionado.telefoneMae || "Não informado"}</p></div>
                                        </div>
                                    </div>
                                    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
                                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">Saúde e Institucional</h3>
                                        <div className="grid grid-cols-1 gap-y-4">
                                            <div><p className="text-xs text-gray-500 mb-1">Restrições de Saúde / Alergias</p><p className="font-medium text-red-600 bg-red-50 p-2 rounded-lg border border-red-100">{alpinistaSelecionado.restricaoSaude || "Nenhuma restrição informada."}</p></div>
                                            <div><p className="text-xs text-gray-500 mb-1">Medicações em Uso</p><p className="font-medium text-gray-900">{alpinistaSelecionado.medicacao || "Nenhuma medicação informada."}</p></div>
                                            {alpinistaSelecionado.is_neurodivergente && (
                                                <div className="bg-indigo-50 border border-indigo-100 p-3 rounded-lg mb-2">
                                                    <p className="text-xs text-indigo-500 font-bold uppercase tracking-wider mb-1">Neurodivergência</p>
                                                    <p className="font-medium text-indigo-900">
                                                        {alpinistaSelecionado.tipo_neurodivergente || "Identificado(a) como neurodivergente."}
                                                    </p>
                                                </div>
                                            )}
                                            
                                        </div>
                                    </div>
                                    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm">
                                        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-4 border-b pb-2">Grupo</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-6">
                                            <div><p className="text-xs text-gray-500 mb-1">Grupo</p><p className="font-medium text-gray-900">{alpinistaSelecionado.grupo || "Não informado"}</p></div>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-6">
    
                                    {/* Encontros como Encontrista */}
                                    <div 
                                        onClick={() => { setAbaHistorico('encontros'); setIsHistoricoGeralOpen(true); }}
                                        title="Clique para ver todos os encontros"
                                        className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm cursor-pointer hover:border-escalada-azul hover:shadow-md hover:ring-2 hover:ring-blue-50 transition-all group"
                                    >
                                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                                            <h3 className="text-sm font-bold text-escalada-azul flex items-center gap-2">
                                                <Calendar size={16} /> Encontros (Encontrista)
                                            </h3>
                                            <Maximize2 size={14} className="text-gray-300 group-hover:text-escalada-azul transition-colors" />
                                        </div>
                                        {alpinistaSelecionado.encontros_realizados && alpinistaSelecionado.encontros_realizados.length > 0 ? (
                                            <ul className="space-y-3">
                                                {alpinistaSelecionado.encontros_realizados.slice(0, 3).map((encontro, idx) => (
                                                    <li key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-100 group-hover:bg-blue-50/50 transition-colors">
                                                        <p className="font-medium text-gray-800 text-sm truncate">{encontro.nome_encontro}</p>
                                                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                            <span className="font-semibold text-escalada-azul uppercase">{encontro.tipo}</span>
                                                            
                                                        </div>
                                                    </li>
                                                ))}
                                                {alpinistaSelecionado.encontros_realizados.length > 3 && (
                                                    <p className="text-xs text-center text-gray-400 mt-2 font-medium">+ {alpinistaSelecionado.encontros_realizados.length - 3} registros...</p>
                                                )}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-gray-500 text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">Nenhum encontro realizado.</p>
                                        )}
                                    </div>

                                    <div 
                                        onClick={() => { setAbaHistorico('equipe'); setIsHistoricoGeralOpen(true); }}
                                        title="Clique para ver todos os trabalhos"
                                        className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm cursor-pointer hover:border-escalada-vermelho hover:shadow-md hover:ring-2 hover:ring-red-50 transition-all group"
                                    >
                                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                                            <h3 className="text-sm font-bold text-escalada-vermelho flex items-center gap-2">
                                                <Briefcase size={16} /> Trabalhos em Equipes
                                            </h3>
                                            <Maximize2 size={14} className="text-gray-300 group-hover:text-escalada-vermelho transition-colors" />
                                        </div>
                                        {alpinistaSelecionado.historico_equipes && alpinistaSelecionado.historico_equipes.length > 0 ? (
                                            <ul className="space-y-3">
                                                {alpinistaSelecionado.historico_equipes.slice(0, 3).map((equipe, idx) => (
                                                    <li key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-100 group-hover:bg-red-50/50 transition-colors">
                                                        <p className="font-medium text-gray-800 text-sm truncate">{equipe.nome_encontro}</p>
                                                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                            <span className="font-semibold text-escalada-vermelho truncate max-w-[100px] text-right">{equipe.equipe}</span>
                                                        </div>
                                                    </li>
                                                ))}
                                                {alpinistaSelecionado.historico_equipes.length > 3 && (
                                                    <p className="text-xs text-center text-gray-400 mt-2 font-medium">+ {alpinistaSelecionado.historico_equipes.length - 3} registros...</p>
                                                )}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-gray-500 text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">Ainda não trabalhou em equipes.</p>
                                        )}
                                    </div>

                                    <div 
                                        onClick={() => { setAbaHistorico('eventos'); setIsHistoricoGeralOpen(true); }}
                                        title="Clique para ver todos os eventos"
                                        className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm cursor-pointer hover:border-yellow-500 hover:shadow-md hover:ring-2 hover:ring-yellow-50 transition-all group"
                                    >
                                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                                            <h3 className="text-sm font-bold text-yellow-600 flex items-center gap-2">
                                                <Ticket size={16} /> Eventos Gerais
                                            </h3>
                                            <Maximize2 size={14} className="text-gray-300 group-hover:text-yellow-500 transition-colors" />
                                        </div>
                                        {alpinistaSelecionado.historico_eventos && alpinistaSelecionado.historico_eventos.length > 0 ? (
                                            <ul className="space-y-3">
                                                {alpinistaSelecionado.historico_eventos.slice(0, 3).map((evento, idx) => (
                                                    <li key={idx} className="bg-gray-50 p-3 rounded-lg border border-gray-100 group-hover:bg-yellow-50/50 transition-colors">
                                                        <p className="font-medium text-gray-800 text-sm truncate">{evento.nome_evento}</p>
                                                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                                                            <span>{evento.data || 'Data Indefinida'}</span>
                                                        </div>
                                                    </li>
                                                ))}
                                                {alpinistaSelecionado.historico_eventos.length > 3 && (
                                                    <p className="text-xs text-center text-gray-400 mt-2 font-medium">+ {alpinistaSelecionado.historico_eventos.length - 3} registros...</p>
                                                )}
                                            </ul>
                                        ) : (
                                            <p className="text-sm text-gray-500 text-center py-4 bg-gray-50 rounded-lg border border-dashed border-gray-200">Nenhuma participação em eventos.</p>
                                        )}
                                    </div>

                                </div>
                            </div>
                        </div>
                    </div>
                </div>,
                document.body
                
            )}
            
            {isMounted && isHistoricoGeralOpen && alpinistaSelecionado && createPortal (
                <div className="fixed inset-0 bg-black/70 z-[9999] flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-gray-50 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-200">
                        
                        <div className="flex justify-between items-center p-6 bg-white border-b border-gray-200">
                            <div className="flex items-center gap-3">
                                <div className="p-3 bg-blue-50 text-escalada-azul rounded-xl border border-blue-100">
                                    <Briefcase size={24} />
                                </div>
                                <div>
                                    <h2 className="text-xl font-bold text-gray-900">Histórico Completo de Participação</h2>
                                    <p className="text-sm text-gray-500">Ficha de <span className="font-semibold text-escalada-azul">{alpinistaSelecionado.nome}</span></p>
                                </div>
                            </div>
                            <button onClick={() => setIsHistoricoGeralOpen(false)} className="text-gray-400 hover:text-gray-800 bg-gray-100 hover:bg-gray-200 p-2 rounded-full transition-colors">
                                <X size={20} />
                            </button>
                        </div>

                        <div className="flex border-b border-gray-200 bg-gray-50 px-6 pt-2">
                            <button onClick={() => setAbaHistorico('encontros')} className={`px-6 py-3 font-bold text-sm border-b-2 ${abaHistorico === 'encontros' ? 'border-escalada-azul text-escalada-azul' : 'border-transparent text-gray-400'}`}>Encontros Realizados</button>
                            <button onClick={() => setAbaHistorico('equipe')} className={`px-6 py-3 font-bold text-sm border-b-2 ${abaHistorico === 'equipe' ? 'border-escalada-vermelho text-escalada-vermelho' : 'border-transparent text-gray-400'}`}>Trabalhos em Equipes</button>
                            <button onClick={() => setAbaHistorico('eventos')} className={`px-6 py-3 font-bold text-sm border-b-2 ${abaHistorico === 'eventos' ? 'border-yellow-500 text-yellow-600' : 'border-transparent text-gray-400'}`}>Eventos Gerais</button>
                        </div>

                        <div className="overflow-y-auto p-6 flex-1 space-y-8">
                            
                            {/* Sessão Completa: Encontros */}
                            {abaHistorico === 'encontros' && (
                                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                                    {encontrosSeguros.length > 0 ? (
                                        <table className="w-full text-left text-sm">
                                            <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
                                                <tr><th className="px-6 py-4">Nome do Encontro</th><th className="px-6 py-4">Tipo</th><th className="px-6 py-4">Grupo</th><th className="px-6 py-4 text-right">Data</th></tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100">
                                                {encontrosSeguros.map((encontro, idx) => (
                                                    <tr key={idx} className="hover:bg-blue-50">
                                                        <td className="px-6 py-4 font-medium text-gray-800">{encontro.nome_encontro}</td>
                                                        <td className="px-6 py-4 text-escalada-azul uppercase font-semibold text-xs">{encontro.tipo}</td>
                                                        <td className="px-6 py-4">
                                                            {encontro.cor_grupo ? (
                                                                <span className="px-2 py-1 rounded-md bg-gray-100 text-gray-700 font-semibold text-xs uppercase border border-gray-200">
                                                                    {encontro.cor_grupo}
                                                                </span>
                                                            ) : '-'}
                                                        </td>
                                                        <td className="px-6 py-4 text-gray-500 text-right">{encontro.data || '-'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    ) : (<p className="text-gray-500 text-center py-10">Nenhum encontro registrado.</p>)}
                                </div>
                            )}

                            {/* Sessão Completa: Equipes */}
                            {abaHistorico === 'equipe' && (
                                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                                    {equipesSeguras.length > 0 ? (
                                        <table className="w-full text-left text-sm">
                                            <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
                                                <tr><th className="px-6 py-4">Equipe</th><th></th><th className="px-6 py-4">Encontro</th><th className="px-6 py-4 text-right">Data</th></tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100">
                                                {equipesSeguras.map((equipe, idx) => (
                                                    <tr key={idx} className="hover:bg-red-50">
                                                        <td className="px-6 py-4 font-bold text-escalada-vermelho">{equipe.equipe}</td>
                                                        <td className="px-6 py-4">
                                                            {equipe.cor_grupo && equipe.equipe.toLowerCase().includes('dirigente') ? (
                                                                <span className="px-2 py-1 rounded-md bg-gray-100 text-gray-700 font-semibold text-xs uppercase border border-gray-200">
                                                                    {equipe.cor_grupo}
                                                                </span>
                                                            ) : '-'}
                                                        </td>
                                                        <td className="px-6 py-4 font-medium text-gray-800">{equipe.nome_encontro}</td>
                                                        <td className="px-6 py-4 text-gray-500 text-right">{equipe.data || '-'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    ) : (<p className="text-gray-500 text-center py-10">Nenhuma participação em equipes.</p>)}
                                </div>
                            )}

                            {/* Sessão Completa: Eventos Gerais */}
                            {abaHistorico === 'eventos' && (
                                <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                                    {eventosSeguros.length > 0 ? (
                                        <table className="w-full text-left text-sm">
                                            <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
                                                <tr><th className="px-6 py-4">Nome do Evento</th><th className="px-6 py-4 text-right">Data</th></tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-100">
                                                {eventosSeguros.map((evento, idx) => (
                                                    <tr key={idx} className="hover:bg-yellow-50">
                                                        <td className="px-6 py-4 font-medium text-gray-800">{evento.nome_evento}</td>
                                                        <td className="px-6 py-4 text-gray-500 text-right">{evento.data || '-'}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    ) : (<p className="text-gray-500 text-center py-10">Nenhum evento registrado.</p>)}
                                </div>
                                )}
                            </div>

                        </div>
                    </div>,
                    document.body
            )}

            {/* Modal de Confirmação de Exclusão (Delete) */}
            {isMounted && isDeleteModalOpen && alpinistaParaDeletar && createPortal (
                <div className="fixed inset-0 bg-black/60 z-[9999] flex items-center justify-center p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
                        <div className="p-6 text-center">
                            <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Trash2 size={32} />
                            </div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">Excluir Alpinista?</h3>
                            <p className="text-sm text-gray-500">Tem certeza que deseja remover <span className="font-bold text-gray-800">{alpinistaParaDeletar.nome}</span>? Esta ação não pode ser desfeita e os dados serão apagados permanentemente.</p>
                        </div>
                        <div className="p-6 bg-gray-50 flex gap-3">
                            <button onClick={() => { setIsDeleteModalOpen(false); setAlpinistaParaDeletar(null); }} disabled={deletando} className="flex-1 px-4 py-2.5 bg-white border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">Cancelar</button>
                            <button onClick={executarDelecao} disabled={deletando} className="flex-1 px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50">{deletando ? "Excluindo..." : "Sim, Excluir"}</button>
                        </div>
                    </div>
                </div>,
                document.body
            )}

        </div>
    );
}