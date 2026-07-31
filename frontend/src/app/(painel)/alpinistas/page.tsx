"use client";

// ============================================================================
// IMPORTAÇÕES
// ============================================================================
import { useState, useEffect } from "react";
// Ícones da biblioteca lucide-react. 
// Filter adicionado para dar um visual legal ao nosso novo dropdown de status.
import { Plus, Search, MoreHorizontal, X, Pencil, Trash2, Filter } from "lucide-react";

// ============================================================================
// INTERFACE (CONTRATO DE DADOS)
// ============================================================================
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

export default function AlpinistasPage() {
    
    // ============================================================================
    // ESTADOS GERAIS E FILTROS DA LISTA
    // ============================================================================
    const [alpinistas, setAlpinistas] = useState<Alpinista[]>([]);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");
    
    // FILTROS
    const [busca, setBusca] = useState(""); // Filtro de Texto (Nome, Email, Tel)
    const [filtroStatus, setFiltroStatus] = useState("TODOS"); // NOVO: Filtro Avançado de Status

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

    const [formData, setFormData] = useState({
        nome: '', email: '', telefone: '', dataNascimento: '',
        endereco: '', nomePai: '', telefonePai: '', nomeMae: '',
        telefoneMae: '', restricaoSaude: '', medicacao: '',
        grupo: '', status: 'ativo'
    });

    // ============================================================================
    // ESTADOS DA FICHA DETALHADA (READ) E EXCLUSÃO (DELETE)
    // ============================================================================
    const [isFichaOpen, setIsFichaOpen] = useState(false);
    const [alpinistaSelecionado, setAlpinistaSelecionado] = useState<Alpinista | null>(null);

    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [alpinistaParaDeletar, setAlpinistaParaDeletar] = useState<Alpinista | null>(null);
    const [deletando, setDeletando] = useState(false);

    // ============================================================================
    // CICLO DE VIDA (useEffect)
    // ============================================================================
    useEffect(() => {
        buscarAlpinistas();
    }, []);

    // ============================================================================
    // INTEGRAÇÃO COM A API (GET, POST, PUT, DELETE)
    // ============================================================================
    const getCookie = (nome: string) => {
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; ${nome}=`);
        if (partes.length === 2) return partes.pop()?.split(';').shift();
        return null;
    };

    const buscarAlpinistas = async () => {
        try {
            const token = getCookie('sia_token');
            if (!token) throw new Error("Token de autenticação não encontrado.");

            const resposta = await fetch("https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/alpinistas/", {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}` 
                }
            });

            if (!resposta.ok) throw new Error("Não foi possível carregar a lista de alpinistas.");

            const dados = await resposta.json();
            setAlpinistas(dados);
        } catch (error: any) {
            setErro(error.message);
        } finally {
            setCarregando(false);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const salvarAlpinista = async (e: React.FormEvent) => {
        e.preventDefault(); 
        setSalvando(true);

        try {
            const token = getCookie('sia_token');
            const dadosParaEnviar = {
                ...formData,
                dataNascimento: formData.dataNascimento === "" ? null : formData.dataNascimento
            };

            const url = idEdicao 
                ? `https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/alpinistas/${idEdicao}/` 
                : "https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/alpinistas";
            
            const metodo = idEdicao ? "PUT" : "POST";

            const resposta = await fetch(url, {
                method: metodo,
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}` 
                },
                body: JSON.stringify(dadosParaEnviar) 
            });

            if (!resposta.ok) throw new Error("Erro ao salvar. Verifique os dados e tente novamente.");

            setIsModalOpen(false); 
            buscarAlpinistas();    

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
            const resposta = await fetch(`https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/alpinistas/${alpinistaParaDeletar.id}/`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${token}` 
                }
            });

            if (!resposta.ok) throw new Error("Não foi possível excluir o alpinista.");

            setIsDeleteModalOpen(false);
            setAlpinistaParaDeletar(null);
            buscarAlpinistas();

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
            grupo: '', status: 'ativo'
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
            grupo: alpinista.grupo || '', status: alpinista.status || 'ativo'
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

    // ============================================================================
    // NOVA LÓGICA DE FILTRO AVANÇADO (FRONT-END)
    // ============================================================================
    const alpinistasFiltrados = alpinistas.filter((alpinista) => {
        // 1. Condição da Barra de Pesquisa (Texto)
        const termoBusca = busca.toLowerCase(); 
        const matchTexto = 
            alpinista.nome.toLowerCase().includes(termoBusca) ||
            (alpinista.email || "").toLowerCase().includes(termoBusca) ||
            (alpinista.telefone || "").toLowerCase().includes(termoBusca);
        
        // 2. Condição da Busca Avançada (Status)
        // Se filtroStatus for "TODOS", aceitamos qualquer um. 
        // Se for específico (ex: "ativo"), comparamos ignorando letras maiúsculas/minúsculas.
        const matchStatus = 
            filtroStatus === "TODOS" || 
            (alpinista.status || "").toLowerCase() === filtroStatus.toLowerCase();

        // O Alpinista só aparece na tabela se passar nos DOIS testes (matchTexto E matchStatus)
        return matchTexto && matchStatus;
    });

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

            </div>

            {/* ÁREA DA TABELA DE DADOS */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden relative">
                
                {menuAberto !== null && <div className="fixed inset-0 z-10" onClick={() => setMenuAberto(null)}></div>}

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
            </div>

            {/* ============================================================================ */}
            {/* MODAIS (CREATE, UPDATE, READ, DELETE) FICAM ABAIXO INTACTOS                  */}
            {/* ============================================================================ */}
            
            {/* Modal de Formulário (Criar/Editar) */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
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
                </div>
            )}

            {/* Modal de Leitura Detalhada (Ficha) */}
            {isFichaOpen && alpinistaSelecionado && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
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
                            <div className="space-y-6">
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
                                        <div><p className="text-xs text-gray-500 mb-1">Grupo Base</p><p className="font-medium text-gray-900">{alpinistaSelecionado.grupo || "Sem grupo definido."}</p></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal de Confirmação de Exclusão (Delete) */}
            {isDeleteModalOpen && alpinistaParaDeletar && (
                <div className="fixed inset-0 bg-black/60 z-[60] flex items-center justify-center p-4">
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
                </div>
            )}

        </div>
    );
}