"use client";

import { useEffect, useState } from "react";
import toast from "react-hot-toast"; 
import Link from "next/link";
import { Settings, Trash2 } from "lucide-react";

const MAPA_STATUS: Record<string, string> = {
  agendado: "Agendado",
  em_agendamento: "Em agendamento",
  cancelado: "Cancelado"
};

export default function Encontros() {

  const [encontros, setEncontros] = useState([]);
  const [carregando, setCarregando] = useState(true);
  const [ordemMaisRecente, setOrdemMaisRecente] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false); 
  const [salvando, setSalvando] = useState(false); 
  
  const [formData, setFormData] = useState({
    encontro: "",
    data_referencia: "", // O dia lógico
    data_exato: "", // Dias do retiro
    local: "Nova Betânia",
    status: "em_agendamento"
  });

  async function carregarEncontros() {
    try {
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
      const resposta = await fetch("https://wpc8m7lx-8000.brs.devtunnels.ms/api/encontros/", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`, // Passaporte de entrada
          "Content-Type": "application/json"  // Idioma da conversa (JSON)
        }
      });

      if (resposta.ok) {
        const dados = await resposta.json();
        setEncontros(dados.results || []);
      } else {
        toast.error("Falha ao buscar os encontros do servidor.");
      }
    } catch (error) {
      toast.error("Erro de conexão com o servidor.");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    carregarEncontros();
  }, []);

  const encontrosOrdenados = [...encontros].sort((a, b) => {
    const dataA = new Date(a.data_referencia).getTime();
    const dataB = new Date(b.data_referencia).getTime();
    return ordemMaisRecente ? dataB - dataA : dataA - dataB;
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Prepara a tela para um NOVO cadastro
  const abrirModalNovo = () => {
    setFormData({ encontro: "", data_referencia: "", data_exato: "", local: "Nova Betânia", status: "em_agendamento" });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); 
    setSalvando(true);

    try {
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
      const url = `https://wpc8m7lx-8000.brs.devtunnels.ms/api/encontros/`;

      const resposta = await fetch(url, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(formData)
      });

      if (resposta.ok) {
        setIsModalOpen(false); // Fecha a janelinha
        carregarEncontros();   // Atualiza a tabela com os novos dados
        
        // Mensagem dinâmica: avisa se criou ou se atualizou
        toast.success("Encontro agendado com sucesso!"); 
      } else {
        toast.error("Não foi possível salvar o encontro.");
      }
    } catch (error) {
      toast.error("Erro ao tentar conectar com o servidor.");
    } finally {
      setSalvando(false); 
    }
  };

  const deletarEncontro = async (id: number) => {
    if (!window.confirm("Tem certeza que deseja excluir este encontro definitivamente?")) return;

    try {
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
      
      // ⚠️ ATENÇÃO: Substitua o link! Notem a interpolação ${id} na URL.
      const resposta = await fetch(`https://wpc8m7lx-8000.brs.devtunnels.ms/api/encontros/${id}/`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`,
        }
      });

      if (resposta.ok) {
        toast.success("Encontro excluído com sucesso!");
        carregarEncontros(); // Recarrega a lista, que agora virá sem o item deletado
      } else {
        toast.error("Erro ao excluir encontro.");
      }
    } catch (error) {
      toast.error("Erro de conexão.");
    }
  };

  return (
    <div className="space-y-6 relative">
      
      {/* CABEÇALHO DA PÁGINA */}
      <div className="flex justify-between items-center bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Encontros</h1>
          <p className="text-gray-500 mt-1">Gerencie os encontros do Movimento Escalada</p>
        </div>
        <button 
          onClick={abrirModalNovo}
          className="bg-escalada-azul hover:bg-blue-800 text-white px-5 py-2.5 rounded-lg font-medium transition-colors shadow-sm"
        >
          + Novo Encontro
        </button>
      </div>

      {carregando ? (
        <p className="p-10 text-center text-gray-500 font-medium">Carregando encontros...</p>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          
          {encontros.length === 0 ? (
            <div className="p-10 text-center text-gray-500">
              Nenhum encontro agendado ainda. Clique no botão acima para criar o primeiro!
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100 text-sm text-gray-500 uppercase tracking-wider">
                    <th className="px-6 py-4 font-medium">Encontro</th>
 
                    <th 
                      className="px-6 py-4 font-medium cursor-pointer hover:text-escalada-azul transition-colors flex items-center gap-1"
                      onClick={() => setOrdemMaisRecente(!ordemMaisRecente)}
                      title="Clique para inverter a ordem"
                    >
                      Data (Referência) {ordemMaisRecente ? "↓" : "↑"}
                    </th>
                    
                    <th className="px-6 py-4 font-medium">Data do Encontro</th>
                    <th className="px-6 py-4 font-medium">Status</th>
                    <th className="px-6 py-4 font-medium text-right">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">

                  {encontrosOrdenados.map((encontro: any) => (
                    <tr key={encontro.id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-medium text-gray-800">{encontro.encontro}</td>
                      
                      <td className="px-6 py-4 text-gray-500 text-sm">
                        {new Date(encontro.data_referencia).toLocaleDateString('pt-BR', { timeZone: 'UTC' })}
                      </td>
                      
                      <td className="px-6 py-4 text-gray-600">{encontro.data_exato}</td>
                      
                      <td className="px-6 py-4">
                        <span className="px-3 py-1 rounded-full text-sm font-medium ${encontro.status === 'agendado' ? 'bg-green-100 text-green-700' : encontro.status === 'em_agendamento' ? 'bg-blue-100 text-blue-700' : 'bg-red-100 text-red-700'}`}" >
                          {MAPA_STATUS[encontro.status] || encontro.status}
                        </span>
                      </td>
                      
                      <td className="px-6 py-4 flex gap-3 justify-end items-center">
                        <Link 
                          href={`encontros/${encontro.id}`}
                          className="flex items-center gap-1 px-4 py-2 bg-escalada-azul/10 hover:bg-escalada-azul/20 text-escalada-azul rounded-lg text-sm font-semibold transition-colors"
                        >
                          <Settings size={16} /> Gerenciar
                        </Link>

                        <button 
                          onClick={() => deletarEncontro(encontro.id)}
                          className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                          title="Excluir Encontro"
                        >
                          < Trash2 size={20} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Novo Encontro</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nome do Encontro</label>
                <input 
                  type="text" 
                  name="encontro" 
                  required 
                  value={formData.encontro}
                  onChange={handleInputChange} 
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul outline-none"
                  placeholder="Ex: Encontro XXXXXXX"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Data de Início
                  </label>
                  <input 
                    type="date" 
                    name="data_referencia"
                    required
                    value={formData.data_referencia}
                    onChange={handleInputChange}
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul outline-none transition-all"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Dias do Encontro
                  </label>
                  <input 
                    type="text" 
                    name="data_exato"
                    required
                    value={formData.data_exato}
                    onChange={handleInputChange}
                    placeholder="Ex: 19, 24, 25 e 26 de Julho"
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul outline-none transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Local</label>
                <input 
                  type="text" 
                  name="local"
                  required
                  value={formData.local}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul outline-none transition-all"
                />
              </div>

              {/* CAMPO STATUS (Seletor do tipo Dropdown) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select 
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-escalada-azul/20 focus:border-escalada-azul outline-none transition-all"
                >
                  <option value="em_agendamento">Em agendamento</option>
                  <option value="agendado">Agendado</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 font-medium text-gray-600 hover:bg-gray-100 rounded-lg transition-colors border border-gray-200"
                >
                  Cancelar
                </button>

                <button 
                  type="submit" 
                  disabled={salvando}
                  className="px-6 py-2 bg-escalada-azul hover:bg-blue-800 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                >
                  {/* Se estiver salvando, muda o texto, senão mostra o texto normal */}
                  {salvando ? "Salvando..." : "Salvar Encontro"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}