// "use client" avisa ao Next.js que este componente precisa rodar no navegador do usuário,
// pois usaremos interatividade (hooks do React como useState e useEffect).
"use client";

import { useEffect, useState } from "react";

export default function Encontros() {
  // ============================================================================
  // 1. ESTADOS DO COMPONENTE (A Memória da Tela)
  // ============================================================================
  
  // Guarda a lista de encontros que virá da API. Começa como um array vazio [].
  const [encontros, setEncontros] = useState([]);
  
  // Controla o feedback visual enquanto os dados não chegam. Começa como true.
  const [carregando, setCarregando] = useState(true);

  // ============================================================================
  // 2. CICLO DE VIDA (O que acontece quando a tela abre)
  // ============================================================================
  
  // useEffect com array vazio [] no final significa: "Rode este bloco APENAS UMA VEZ
  // assim que a tela terminar de carregar no navegador".
  useEffect(() => {
    async function carregarEncontros() {
      try {
        // Passo A: Resgatar o token de segurança salvo nos cookies do navegador.
        // O Regex abaixo procura especificamente pelo cookie chamado "sia_token".
        const token = document.cookie.replace(/(?:(?:^|.*;\s*)sia_token\s*\=\s*([^;]*).*$)|^.*$/, "$1");

        // Passo B: Disparar a requisição GET para a rota de encontros no Back-end (Django).
        // ATENÇÃO: Substitua pela URL pública da sua porta 8000 no Codespaces!
        const resposta = await fetch("https://reimagined-space-eureka-97p4jpg66pwh4qx-3000.app.github.dev/api/encontros/", {
          headers: {
            "Authorization": `Bearer ${token}`, // Passaporte de entrada
            "Content-Type": "application/json"  // Formato da conversa
          }
        });

        // Passo C: Verificar se o servidor autorizou e devolveu os dados com sucesso (Status 200).
        if (resposta.ok) {
          const dados = await resposta.json(); // Traduz de JSON para objeto JavaScript
          setEncontros(dados); // Salva os dados no estado, o que forçará a tela a se desenhar novamente
        } else {
          console.error("Falha ao buscar encontros. Status:", resposta.status);
        }
      } catch (error) {
        // Se a internet cair ou a URL do Codespaces mudar, o erro cai aqui.
        console.error("Erro fatal na requisição:", error);
      } finally {
        // Passo D: Independentemente de ter dado certo ou errado, avisamos que terminou de carregar.
        setCarregando(false);
      }
    }

    // Executa a função que acabamos de declarar acima.
    carregarEncontros();
  }, []);

  // ============================================================================
  // 3. RENDERIZAÇÃO (O Visual da Tela - HTML/Tailwind)
  // ============================================================================
  
  return (
    <div className="p-8">
      
      {/* CABEÇALHO DA TELA */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">Encontros</h1>
          <p className="text-gray-500 mt-1">Gerencie os eventos do Movimento Escalada</p>
        </div>
        
        {/* Botão que futuramente vai abrir o modal/formulário de criação */}
        <button className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors">
          + Novo Encontro
        </button>
      </div>

      {/* 
        REGRA DE EXIBIÇÃO TERNÁRIA:
        Se 'carregando' for verdadeiro ? Mostra o texto de carregamento 
        : (Senão) Mostra a tabela de dados
      */}
      {carregando ? (
        <p className="text-gray-500">Carregando encontros...</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          
          {/* Validação de Estado Vazio (Empty State) */}
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
                  <th className="p-4 font-semibold text-gray-600">Data</th>
                  <th className="p-4 font-semibold text-gray-600">Local</th>
                  <th className="p-4 font-semibold text-gray-600">Status</th>
                </tr>
              </thead>
              <tbody>
                {/* 
                  Iteração (Map): Percorre o array de encontros e cria uma linha (<tr>) para cada um.
                  A propriedade 'key' é obrigatória no React para otimização de performance.
                */}
                {encontros.map((encontro: any) => (
                  <tr key={encontro.id} className="border-b border-gray-50 hover:bg-gray-50 transition-colors">
                    <td className="p-4 font-medium text-gray-800">{encontro.tema}</td>
                    
                    {/* Convertemos a string do banco (YYYY-MM-DD) para o formato brasileiro (DD/MM/YYYY) */}
                    <td className="p-4 text-gray-600">
                      {new Date(encontro.data_encontro).toLocaleDateString('pt-BR')}
                    </td>
                    
                    <td className="p-4 text-gray-600">{encontro.local}</td>
                    
                    {/* Estilização condicional simples no status (pode ser aprimorada depois) */}
                    <td className="p-4">
                      <span className="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-700">
                        {encontro.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}