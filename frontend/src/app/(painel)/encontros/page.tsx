// A diretiva "use client" é obrigatória no Next.js (App Router) sempre que formos usar 
// interatividade no navegador, como botões, formulários e estados (useState).
"use client";

// Importamos os "Hooks" do React (ferramentas que dão poderes ao nosso componente)
import { useEffect, useState } from "react";
// Importamos a biblioteca de notificações elegantes que instalamos
import toast from "react-hot-toast"; 

// ============================================================================
// DICIONÁRIO DE STATUS (Padrão de Projeto: Mapa de Valores)
// ============================================================================
// O banco de dados prefere guardar dados padronizados, minúsculos e sem espaços (ex: em_agendamento).
// Porém, o usuário precisa de uma interface amigável. Esse objeto serve como um "tradutor".
const MAPA_STATUS: Record<string, string> = {
  agendado: "Agendado",
  em_agendamento: "Em agendamento",
  cancelado: "Cancelado"
};

export default function Encontros() {
  // ============================================================================
  // 1. ESTADOS DO COMPONENTE (A Memória da Tela)
  // ============================================================================
  
  // 'encontros' guarda a lista que vem do Back-end. Começa como um array vazio [].
  const [encontros, setEncontros] = useState([]);
  
  // 'carregando' avisa a tela se os dados ainda estão vindo pela internet. Começa como true.
  const [carregando, setCarregando] = useState(true);

  // Se true, os encontros mais recentes ficam no topo. Se false, inverte a ordem.
  const [ordemMaisRecente, setOrdemMaisRecente] = useState(true);
  
  // 'isModalOpen' controla se a janela de "Novo Encontro" está visível (true) ou invisível (false).
  const [isModalOpen, setIsModalOpen] = useState(false); 
  
  // 'salvando' desabilita o botão de salvar enquanto o servidor processa, evitando cliques duplos.
  const [salvando, setSalvando] = useState(false); 

  // Se for null, o React entende que o usuário quer CRIAR um encontro novo (POST).
  // Se tiver um número (ex: 5), o React entende que o usuário quer ATUALIZAR (PUT).
  const [idEditando, setIdEditando] = useState<number | null>(null);
  
  // 'formData' é um objeto que guarda em tempo real tudo o que o usuário digita no formulário.
  // Já deixamos valores padrão ('Sede do Movimento' e 'agendado') para facilitar a vida do usuário.
  const [formData, setFormData] = useState({
    encontro: "",
    data_referencia: "", // O dia lógico
    data_exato: "", // Dias do retiro
    local: "Nova Betânia",
    status: "em_agendamento"
  });

  // ============================================================================
  // 2. FUNÇÕES DE COMUNICAÇÃO COM A API (A Leitura de Dados - GET)
  // ============================================================================
  
  // Função assíncrona (async) porque dependemos do tempo de resposta da internet
  async function carregarEncontros() {
    try {
      // Pega o token de segurança salvo no navegador para provar ao Django que estamos logados
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
      const resposta = await fetch("https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/encontros/", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`, // Passaporte de entrada
          "Content-Type": "application/json"  // Idioma da conversa (JSON)
        }
      });

      if (resposta.ok) {
        // Se o Django autorizou (Status 200), transformamos o texto em um objeto JavaScript
        const dados = await resposta.json();
        // E salvamos na "memória" da tela, o que faz a tabela ser desenhada com os dados
        setEncontros(dados);
      } else {
        // Se deu erro de permissão ou a URL estiver errada, avisamos com o Toast vermelho
        toast.error("Falha ao buscar os encontros do servidor.");
      }
    } catch (error) {
      // Se a internet cair completamente, cai neste bloco
      toast.error("Erro de conexão com o servidor.");
    } finally {
      // O 'finally' sempre executa no final, dando certo ou errado. 
      // Usamos para esconder a mensagem de "Carregando..."
      setCarregando(false);
    }
  }

  // O useEffect com o array vazio [] no final garante que a função carregarEncontros()
  // seja chamada APENAS UMA VEZ, no exato momento em que o usuário abre esta tela.
  useEffect(() => {
    carregarEncontros();
  }, []);

  // ============================================================================
  // 3. LÓGICA DE ORDENAÇÃO (No Front-end)
  // ============================================================================
  // Usamos o operador spread [...encontros] para criar uma cópia exata da lista original.
  // Regra de Ouro do React: NUNCA altere o estado original diretamente (mutabilidade).
  const encontrosOrdenados = [...encontros].sort((a, b) => {
    // Transformamos as datas de texto em "Tempo absoluto" (milissegundos) para a matemática funcionar
    const dataA = new Date(a.data_referencia).getTime();
    const dataB = new Date(b.data_referencia).getTime();
    
    // Se ordemMaisRecente for TRUE, a matemática (B - A) coloca as datas maiores (mais no futuro) em cima.
    // Se for FALSE, (A - B) inverte tudo.
    return ordemMaisRecente ? dataB - dataA : dataA - dataB;
  });

  // ============================================================================
  // 4. FUNÇÕES DE INTERAÇÃO (Formulário e Criação - POST)
  // ============================================================================
  
  // Atualiza o formData letra por letra enquanto o usuário digita
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Prepara a tela para um NOVO cadastro
  const abrirModalNovo = () => {
    setIdEditando(null); // Garante que não tem ID (Modo Criação)
    setFormData({ encontro: "", data_referencia: "", data_exato: "", local: "Sede do Movimento", status: "em_agendamento" });
    setIsModalOpen(true);
  };

  // Prepara a tela para EDITAR um cadastro existente
  const abrirModalEditar = (encontro: any) => {
    setIdEditando(encontro.id); // Salva o ID na memória (Modo Edição)
    
    // Puxa os dados antigos do banco e joga nos inputs para o usuário não precisar digitar tudo de novo
    setFormData({
      encontro: encontro.encontro,
      data_referencia: encontro.data_referencia,
      data_exato: encontro.data_exato,
      local: encontro.local,
      status: encontro.status
    });
    setIsModalOpen(true);
  };

  // ============================================================================
  // 5. SALVAR DADOS (POST ou PUT)
  // ============================================================================
  // Esta função é disparada quando o usuário clica no botão "Salvar Encontro" (tipo submit)
  const handleSubmit = async (e: React.FormEvent) => {
    // O preventDefault bloqueia o comportamento jurássico do HTML de tentar recarregar a página inteira
    e.preventDefault(); 
    // Muda o botão para o modo "Salvando..."
    setSalvando(true);

    try {
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");

      // ⚠️ ATENÇÃO: Substitua o link base!
      // Se tivermos um ID na memória, a URL ganha uma barra e o ID no final (ex: /encontros/5/).
      const url = idEditando 
        ? `https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/encontros/${idEditando}/`
        : `https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/encontros/`;
        
      // Se tivermos um ID, usamos PUT (Atualizar). Se for nulo, usamos POST (Criar).
      const metodo = idEditando ? "PUT" : "POST";

      const resposta = await fetch(url, {
        method: metodo,
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
        toast.success(idEditando ? "Encontro atualizado!" : "Encontro agendado com sucesso!"); 
      } else {
        toast.error("Não foi possível salvar o encontro.");
      }
    } catch (error) {
      toast.error("Erro ao tentar conectar com o servidor.");
    } finally {
      setSalvando(false); 
    }
  };

  // ============================================================================
  // 6. EXCLUIR DADOS (DELETE)
  // ============================================================================
  const deletarEncontro = async (id: number) => {
    // window.confirm é um recurso nativo do navegador para evitar cliques acidentais
    if (!window.confirm("Tem certeza que deseja excluir este encontro definitivamente?")) return;

    try {
      const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");
      
      // ⚠️ ATENÇÃO: Substitua o link! Notem a interpolação ${id} na URL.
      const resposta = await fetch(`https://reimagined-space-eureka-97p4jpg66pwh4qx-8000.app.github.dev/api/encontros/${id}/`, {
        method: "DELETE", // Método HTTP específico para destruir registros
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

  // ============================================================================
  // 7. RENDERIZAÇÃO (O Visual da Tela - HTML + Tailwind CSS)
  // ============================================================================
  return (
    // 'relative' é necessário aqui para que o modal consiga se sobrepor a esta tela inteira
    <div className="p-8 relative">
      
      {/* CABEÇALHO DA PÁGINA */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Encontros</h1>
          <p className="text-gray-500 mt-1">Gerencie os encontros do Movimento Escalada</p>
        </div>
        
        {/* BOTÃO DE NOVO ENCONTRO:
            O evento onClick muda o estado 'isModalOpen' para true, o que faz o React
            renderizar o bloco de código do modal que está lá embaixo. */}
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors"
        >
          + Novo Encontro
        </button>
      </div>

      {/* ÁREA DE CONTEÚDO (Lista ou Loading) 
          Usamos uma condição ternária (condição ? verdadeiro : falso) */}
      {carregando ? (
        <p className="text-gray-500">Carregando encontros...</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          
          {/* Se o array estiver vazio, mostramos uma mensagem amigável (Empty State) */}
          {encontros.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              Nenhum encontro agendado ainda. Clique no botão acima para criar o primeiro!
            </div>
          ) : (
            
            /* TABELA DE DADOS */
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="p-4 font-semibold text-gray-600">Encontro</th>
                  
                  {/* 
                    Cabeçalho de Data Interativo:
                    O onClick inverte o booleano 'ordemMaisRecente' (se era true, vira false e vice-versa).
                    O ícone de setinha (↓ / ↑) muda dinamicamente para indicar o sentido visualmente.
                  */}
                  <th 
                    className="p-4 font-semibold text-gray-600 cursor-pointer hover:bg-gray-200 transition-colors"
                    onClick={() => setOrdemMaisRecente(!ordemMaisRecente)}
                    title="Clique para inverter a ordem"
                  >
                    Data (Referência) {ordemMaisRecente ? "↓" : "↑"}
                  </th>
                  
                  <th className="p-4 font-semibold text-gray-600">Data do Encontro</th>
                  <th className="p-4 font-semibold text-gray-600">Status</th>
                  
                  <th className="p-4 font-semibold text-gray-600 text-center">Ações</th>
                </tr>
              </thead>
              <tbody>
                {/* 
                  Usamos 'encontrosOrdenados' aqui em vez do 'encontros' original. 
                  Isso faz a tabela reagir imediatamente quando o usuário clica no cabeçalho da data.
                */}
                {encontrosOrdenados.map((encontro: any) => (
                  <tr key={encontro.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="p-4 font-medium text-gray-800">{encontro.encontro}</td>
                    
                    {/* Renderiza a data no padrão Brasileiro */}
                    <td className="p-4 text-gray-500 text-sm">
                      {new Date(encontro.data_referencia).toLocaleDateString('pt-BR', { timeZone: 'UTC' })}
                    </td>
                    
                    <td className="p-4 text-gray-600">{encontro.data_exato}</td>
                    
                    <td className="p-4">
                      {/* O Dicionário em ação: procuramos a chave 'encontro.status'. 
                          Se ela existir no MAPA_STATUS, exibe a versão bonita. Senão, mostra como veio. */}
                      <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                        {MAPA_STATUS[encontro.status] || encontro.status}
                      </span>
                    </td>
                    
                    {/* BOTÕES DE AÇÃO: Editar e Excluir */}
                    <td className="p-4 flex gap-2 justify-center">
                      <button 
                        onClick={() => abrirModalEditar(encontro)}
                        className="px-3 py-1 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-md text-sm transition-colors"
                      >
                        Editar
                      </button>
                      <button 
                        onClick={() => deletarEncontro(encontro.id)}
                        className="px-3 py-1 bg-red-100 hover:bg-red-200 text-red-700 rounded-md text-sm transition-colors"
                      >
                        Excluir
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* ============================================================================
          8. MODAL DE CADASTRO (A Janela Sobreposta)
          ============================================================================ */}
      
      {/* 
        A sintaxe && no React significa: "Se a variável da esquerda for TRUE, renderize o HTML da direita".
        Portanto, este HTML inteiro só existe na tela se o botão "+ Novo Encontro" for clicado.
      */}
      {isModalOpen && (
        // OVERLAY: O fundo preto semi-transparente que cobre a tela toda (fixed inset-0)
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          
          {/* CAIXA BRANCA: O modal em si, centralizado pelos comandos do overlay acima */}
          <div className="bg-white rounded-xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Novo Encontro</h2>
            
            {/* O evento onSubmit é a forma correta de capturar o clique do botão "Salvar" 
                ou o "Enter" do teclado dentro do formulário. */}
            <form onSubmit={handleSubmit} className="space-y-4">
              
              {/* CAMPO: encontro */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Encontro</label>
                <input 
                  type="text" 
                  name="encontro" // O nome precisa ser EXATAMENTE igual à chave lá no 'formData' do começo
                  required // HTML5 avisa que o campo é obrigatório
                  value={formData.encontro} // Faz o campo mostrar o que está salvo na memória
                  onChange={handleInputChange} // Avisa a memória a cada nova letra digitada
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="Ex: Encontro de Boas-Vindas"
                />
              </div>

              {/* DATAS (Referência Lógica + Frase Visual) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* 1. O Calendário para o banco ordenar */}
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
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
                
                {/* 2. O Texto Livre que vai para a tabela */}
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
                    className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* CAMPO: LOCAL */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Local</label>
                <input 
                  type="text" 
                  name="local"
                  required
                  value={formData.local}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
              </div>

              {/* CAMPO STATUS (Seletor do tipo Dropdown) */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                <select 
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                >
                  <option value="em_agendamento">Em agendamento</option>
                  <option value="agendado">Agendado</option>
                  <option value="cancelado">Cancelado</option>
                </select>
              </div>

              {/* ÁREA DOS BOTÕES */}
              <div className="flex justify-end gap-3 mt-8">
                {/* Botão de Cancelar: apenas volta o 'isModalOpen' para false, fechando a janela */}
                <button 
                  type="button" 
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                >
                  Cancelar
                </button>
                
                {/* Botão de Salvar: o type="submit" é o que aciona o onSubmit lá em cima na tag <form> */}
                <button 
                  type="submit" 
                  disabled={salvando} // Se já estiver salvando, o botão fica inativo (cinza)
                  className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
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