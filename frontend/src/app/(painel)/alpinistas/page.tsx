"use client";

import { useState, useEffect } from "react";
import { Plus, Search, MoreHorizontal, X } from "lucide-react"; // Adicionamos o X para o Modal

// Sua interface completa
interface Alpinista {
    id: number;
    nome: string;
    email: string;
    telefone: string;
    dataNascimento: number; // Nota: Inputs de data no HTML retornam string (ex: "2000-01-25"). O Django costuma converter isso automaticamente.
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
    const [alpinistas, setAlpinistas] = useState<Alpinista[]>([]);
    const [carregando, setCarregando] = useState(true);
    const [erro, setErro] = useState("");

    // --- ESTADOS DO MODAL E FORMULÁRIO ---
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [salvando, setSalvando] = useState(false);

    // Em vez de 13 states diferentes, usamos um único objeto para agrupar os dados do formulário.
    // Isso é uma excelente prática de arquitetura para formulários grandes!
    const [formData, setFormData] = useState({
        nome: '', email: '', telefone: '', dataNascimento: '',
        endereco: '', nomePai: '', telefonePai: '', nomeMae: '',
        telefoneMae: '', restricaoSaude: '', medicacao: '',
        grupo: '', status: 'Ativo' // Valor padrão inicial
    });

    useEffect(() => {
        buscarAlpinistas();
    }, []);

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

            const resposta = await fetch("http://localhost:8000/api/alpinistas/", {
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

    // Função universal para atualizar qualquer campo do formulário dinamicamente
    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    // Função de CREATE (POST) adaptada para enviar o objeto completo
    const salvarAlpinista = async (e: React.FormEvent) => {
        e.preventDefault();
        setSalvando(true);

        try {
            const token = getCookie('sia_token');
            
            const resposta = await fetch("http://localhost:8000/api/alpinistas/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}` 
                },
                body: JSON.stringify(formData) // Enviamos o objeto completo para o Django
            });

            if (!resposta.ok) {
                // Se o Django reclamar de algum campo obrigatório faltando, mostramos o erro
                const erroData = await resposta.json().catch(() => null);
                console.error("Erro do Django:", erroData);
                throw new Error("Erro ao salvar. Verifique os dados e tente novamente.");
            }

            setIsModalOpen(false); // Fecha o modal
            
            // Reseta o formulário para o estado inicial vazio
            setFormData({
                nome: '', email: '', telefone: '', dataNascimento: '',
                endereco: '', nomePai: '', telefonePai: '', nomeMae: '',
                telefoneMae: '', restricaoSaude: '', medicacao: '',
                grupo: '', status: 'Ativo'
            });
            
            buscarAlpinistas(); // Recarrega a tabela

        } catch (error: any) {
            alert(error.message);
        } finally {
            setSalvando(false);
        }
    };

    return (
        <div className="space-y-6 relative">
            
            {/* Cabeçalho */}
            <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
                <div>
                    <h1 className="text-2xl font-bold text-gray-800">Alpinistas</h1>
                    <p className="text-sm text-gray-500 mt-1">Gerencie os membros do Movimento Escalada.</p>
                </div>
                <button 
                    onClick={() => setIsModalOpen(true)}
                    className="bg-escalada-azul hover:bg-blue-800 text-white px-5 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-colors shadow-sm"
                >
                    <Plus size={20} />
                    Novo Alpinista
                </button>
            </div>

            {/* Barra de Pesquisa */}
            <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex gap-4">
                <div className="flex-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <Search className="h-5 w-5 text-gray-400" />
                    </div>
                    <input 
                        type="text" 
                        placeholder="Buscar por nome, email ou telefone..." 
                        className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul transition-all"
                    />
                </div>
            </div>

            {/* Tabela de Dados (Mantida exatamente como você personalizou) */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                {carregando && <div className="p-10 text-center text-gray-500 font-medium">Carregando dados do banco...</div>}
                {erro && <div className="p-10 text-center text-red-500 font-medium bg-red-50">{erro}</div>}
                
                {!carregando && !erro && alpinistas.length === 0 && (
                    <div className="p-10 text-center text-gray-500">
                        Nenhum alpinista cadastrado ainda. Clique em "Novo Alpinista" para começar.
                    </div>
                )}

                {!carregando && !erro && alpinistas.length > 0 && (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-gray-50 border-b border-gray-100 text-sm text-gray-500 uppercase tracking-wider">
                                    <th className="px-6 py-4 font-medium">Nome</th>
                                    <th className="px-6 py-4 font-medium">E-mail</th>
                                    <th className="px-6 py-4 font-medium">Telefone</th>
                                    <th className="px-6 py-4 font-medium text-right">Ações</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                                {alpinistas.map((alpinista) => (
                                    <tr key={alpinista.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-6 py-6 flex items-center gap-4">
                                            {alpinista.foto ? (
                                                <img src={alpinista.foto} alt={`Foto de ${alpinista.nome}`} className="w-12 h-12 rounded-full object-cover border border-gray-200" />
                                            ) : (
                                                <div className="w-12 h-12 rounded-full bg-blue-50 text-escalada-azul flex items-center justify-center font-bold text-sm border border-blue-100">
                                                    {alpinista.nome.charAt(0).toUpperCase()}
                                                </div>
                                            )}
                                            <span className="text-base font-medium text-gray-900">{alpinista.nome}</span>
                                        </td>
                                        <td className="px-6 py-6 text-sm text-gray-500">{alpinista.email || "Não informado"}</td>
                                        <td className="px-6 py-6 text-sm text-gray-500">{alpinista.telefone || "Não informado"}</td>
                                        <td className="px-6 py-6 text-sm text-right">
                                            <button className="text-gray-400 hover:text-escalada-azul transition-colors p-2 rounded-lg hover:bg-blue-50">
                                                <MoreHorizontal size={24} />
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* --- MODAL DE CRIAÇÃO --- */}
            {isModalOpen && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
                    {/* Aumentamos a largura máxima (max-w-3xl) e definimos uma altura máxima com scroll (max-h-[90vh]) */}
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
                        
                        {/* Cabeçalho Fixo do Modal */}
                        <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-white">
                            <h2 className="text-xl font-bold text-gray-800">Cadastrar Novo Alpinista</h2>
                            <button onClick={() => setIsModalOpen(false)} className="text-gray-400 hover:text-gray-600 transition-colors">
                                <X size={24} />
                            </button>
                        </div>

                        {/* Corpo do Formulário com Scroll Interno */}
                        <div className="overflow-y-auto p-6 flex-1">
                            <form id="form-alpinista" onSubmit={salvarAlpinista} className="space-y-6">
                                
                                {/* Seção: Dados Pessoais */}
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Dados Pessoais</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="md:col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Nome Completo *</label>
                                            <input type="text" name="nome" required value={formData.nome} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
                                            <input type="email" name="email" value={formData.email} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
                                            <input type="tel" name="telefone" value={formData.telefone} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Data de Nascimento</label>
                                            <input type="date" name="dataNascimento" value={formData.dataNascimento} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div className="md:col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
                                            <input type="text" name="endereco" value={formData.endereco} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                    </div>
                                </div>

                                {/* Seção: Filiação */}
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Filiação</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Pai/Resp</label>
                                            <input type="text" name="nomePai" value={formData.nomePai} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Telefone do Pai/Resp</label>
                                            <input type="tel" name="telefonePai" value={formData.telefonePai} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Nome da Mãe/Resp</label>
                                            <input type="text" name="nomeMae" value={formData.nomeMae} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Telefone da Mãe/Resp</label>
                                            <input type="tel" name="telefoneMae" value={formData.telefoneMae} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                    </div>
                                </div>

                                {/* Seção: Saúde e Institucional */}
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Saúde e Institucional</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <div className="md:col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Restrições de Saúde</label>
                                            <input type="text" name="restricaoSaude" value={formData.restricaoSaude} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" placeholder="Alergias, condições, etc." />
                                        </div>
                                        <div className="md:col-span-2">
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Medicações em Uso</label>
                                            <input type="text" name="medicacao" value={formData.medicacao} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Grupo</label>
                                            <input type="text" name="grupo" value={formData.grupo} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                                            <select name="status" value={formData.status} onChange={handleChange} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul bg-white">
                                                <option value="Ativo">Ativo</option>
                                                <option value="Inativo">Inativo</option>
                                                <option value="Pendente">Pendente</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </form>
                        </div>

                        {/* Rodapé Fixo do Modal */}
                        <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 rounded-b-2xl">
                            <button 
                                type="button" 
                                onClick={() => setIsModalOpen(false)} 
                                className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors shadow-sm"
                            >
                                Cancelar
                            </button>
                            {/* O atributo form="form-alpinista" conecta este botão ao formulário lá em cima, permitindo que ele dê o submit mesmo estando fora da tag <form> */}
                            <button 
                                type="submit" 
                                form="form-alpinista" 
                                disabled={salvando} 
                                className="px-5 py-2.5 text-sm font-medium text-white bg-escalada-azul hover:bg-blue-800 rounded-lg transition-colors shadow-sm disabled:opacity-50"
                            >
                                {salvando ? "Salvando..." : "Salvar Alpinista"}
                            </button>
                        </div>

                    </div>
                </div>
            )}

        </div>
    );
}