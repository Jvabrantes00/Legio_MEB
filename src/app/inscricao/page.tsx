"use client";

import { useState } from "react";

// Função mágica que cria a máscara do telefone automaticamente
const formatarTelefone = (valor: string) => {
  const v = valor.replace(/\D/g, "");
  
  if (v.length <= 2) return v;
  if (v.length <= 6) return `(${v.slice(0, 2)}) ${v.slice(2)}`;
  if (v.length <= 10) return `(${v.slice(0, 2)}) ${v.slice(2, 6)}-${v.slice(6)}`;
  
  return `(${v.slice(0, 2)}) ${v.slice(2, 7)}-${v.slice(7, 11)}`;
};

export default function InscricaoPublicaPage() {
  // 1. Dados Pessoais
  const [nome, setNome] = useState("");
  const [dataNascimento, setDataNascimento] = useState("");
  const [endereco, setEndereco] = useState("");
  
  // 2. Contatos
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  
  // 3. Filiação
  const [nomePai, setNomePai] = useState("");
  const [telefonePai, setTelefonePai] = useState("");
  const [nomeMae, setNomeMae] = useState("");
  const [telefoneMae, setTelefoneMae] = useState("");
  
  // Estado para controlar o erro da filiação
  const [erroFiliacao, setErroFiliacao] = useState("");

  // 4. Saúde
  const [temRestricao, setTemRestricao] = useState("nao");
  const [qualRestricao, setQualRestricao] = useState("");
  const [tomaMedicacao, setTomaMedicacao] = useState("nao");
  const [detalhesMedicacao, setDetalhesMedicacao] = useState("");

  // 5. Histórico no Movimento
  const [conheciaEscalada, setConheciaEscalada] = useState("nao");
  const [grupoPosEncontro, setGrupoPosEncontro] = useState("");

  const [enviado, setEnviado] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const temAlgumNome = nomePai.trim() !== "" || nomeMae.trim() !== "";
    const temAlgumTelefone = telefonePai.trim() !== "" || telefoneMae.trim() !== "";

    if (!temAlgumNome || !temAlgumTelefone) {
      setErroFiliacao("Por favor, preencha pelo menos um NOME e um TELEFONE de contato de emergência.");
      document.getElementById("secao-filiacao")?.scrollIntoView({ behavior: "smooth", block: "center" });
      return; 
    }
    
    setErroFiliacao("");
    
    // 1. Cria o objeto do novo alpinista com um ID falso e status "Pendente"
    const novoAlpinista = {
      id: Date.now(), // Gera um ID único baseado na hora
      nome, 
      email, 
      telefone,
      status: "Pendente" // Quem vem do site entra como pendente!
    };

    // 2. Puxa os dados que já existem na memória do navegador (ou cria uma lista vazia)
    const alpinistasSalvos = JSON.parse(localStorage.getItem("novosAlpinistas") || "[]");
    
    // 3. Adiciona o novo alpinista na lista e salva de volta na memória
    alpinistasSalvos.push(novoAlpinista);
    localStorage.setItem("novosAlpinistas", JSON.stringify(alpinistasSalvos));

    console.log("Inscrição salva com sucesso no localStorage:", novoAlpinista);
    setEnviado(true);
  };

  if (enviado) {
    return (
      <div className="min-h-screen bg-blue-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-sm text-center border border-blue-100">
          <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 13l4 4L19 7"></path></svg>
          </div>
          <h2 className="text-2xl font-bold text-black mb-2">Inscrição Recebida!</h2>
          <p className="text-black mb-6">Seus dados foram enviados com sucesso. Em breve a coordenação entrará em contato.</p>
          <button onClick={() => setEnviado(false)} className="text-blue-600 font-bold hover:underline">
            Fazer nova inscrição
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-blue-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">
        
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-black">Ficha de Inscrição</h1>
          <p className="text-black mt-2">Preencha seus dados para participar do Movimento Escalada.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8 bg-white p-8 rounded-2xl shadow-md border border-blue-100">
          
          {/* SESSÃO 1: Dados Pessoais */}
          <section>
            <h2 className="text-xl font-bold text-black mb-4 border-b border-gray-200 pb-2">1. Dados Pessoais</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-black mb-1">Nome Completo *</label>
                <input type="text" required value={nome} onChange={(e) => setNome(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" />
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Data de Nascimento *</label>
                <input type="date" required value={dataNascimento} onChange={(e) => setDataNascimento(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" />
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Telefone / WhatsApp *</label>
                <input 
                  type="tel" 
                  required 
                  maxLength={15}
                  value={telefone} 
                  onChange={(e) => setTelefone(formatarTelefone(e.target.value))} 
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" 
                  placeholder="(00) 00000-0000" 
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-black mb-1">E-mail *</label>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-bold text-black mb-1">Endereço Completo *</label>
                <input type="text" required value={endereco} onChange={(e) => setEndereco(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" placeholder="Rua, Número, Bairro, Cidade" />
              </div>
            </div>
          </section>

          {/* SESSÃO 2: Filiação */}
          <section id="secao-filiacao">
            <h2 className="text-xl font-bold text-black mb-4 border-b border-gray-200 pb-2">2. Filiação (Contatos de Emergência) *</h2>
            
            {erroFiliacao && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-sm font-medium">
                {erroFiliacao}
              </div>
            )}

            <p className="text-sm text-gray-600 mb-4">É obrigatório informar pelo menos um NOME e um TELEFONE para emergências.</p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div>
                <label className="block text-sm font-bold text-black mb-1">Nome do Pai ou Responsável</label>
                <input type="text" value={nomePai} onChange={(e) => setNomePai(e.target.value)} className={`w-full px-4 py-2 border ${erroFiliacao && !nomePai && !nomeMae ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-lg focus:ring-2 outline-none text-black`} />
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Telefone do Pai ou Responsável</label>
                <input 
                  type="tel" 
                  maxLength={15}
                  value={telefonePai} 
                  onChange={(e) => setTelefonePai(formatarTelefone(e.target.value))} 
                  className={`w-full px-4 py-2 border ${erroFiliacao && !telefonePai && !telefoneMae ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-lg focus:ring-2 outline-none text-black`}
                  placeholder="(00) 00000-0000"
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Nome da Mãe ou Responsável</label>
                <input type="text" value={nomeMae} onChange={(e) => setNomeMae(e.target.value)} className={`w-full px-4 py-2 border ${erroFiliacao && !nomePai && !nomeMae ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-lg focus:ring-2 outline-none text-black`} />
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Telefone da Mãe ou Responsável</label>
                <input 
                  type="tel" 
                  maxLength={15}
                  value={telefoneMae} 
                  onChange={(e) => setTelefoneMae(formatarTelefone(e.target.value))} 
                  className={`w-full px-4 py-2 border ${erroFiliacao && !telefonePai && !telefoneMae ? 'border-red-300 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'} rounded-lg focus:ring-2 outline-none text-black`}
                  placeholder="(00) 00000-0000"
                />
              </div>
            </div>
          </section>

          {/* SESSÃO 3: Saúde e Segurança */}
          <section>
            <h2 className="text-xl font-bold text-black mb-4 border-b border-gray-200 pb-2">3. Saúde e Segurança</h2>
            <div className="space-y-5">
              
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                <label className="block text-sm font-bold text-black mb-2">Possui alguma restrição alimentar ou alergia?</label>
                <div className="flex gap-4 mb-3">
                  <label className="flex items-center gap-2 cursor-pointer text-black">
                    <input type="radio" name="restricao" value="nao" checked={temRestricao === 'nao'} onChange={(e) => setTemRestricao(e.target.value)} className="w-4 h-4 text-blue-600" /> Não
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-black">
                    <input type="radio" name="restricao" value="sim" checked={temRestricao === 'sim'} onChange={(e) => setTemRestricao(e.target.value)} className="w-4 h-4 text-blue-600" /> Sim
                  </label>
                </div>
                {temRestricao === 'sim' && (
                  <input type="text" required value={qualRestricao} onChange={(e) => setQualRestricao(e.target.value)} placeholder="Qual? Ex: Intolerância à lactose, alergia a amendoim..." className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none mt-2 text-black" />
                )}
              </div>

              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                <label className="block text-sm font-bold text-black mb-2">Toma alguma medicação de uso contínuo?</label>
                <div className="flex gap-4 mb-3">
                  <label className="flex items-center gap-2 cursor-pointer text-black">
                    <input type="radio" name="medicacao" value="nao" checked={tomaMedicacao === 'nao'} onChange={(e) => setTomaMedicacao(e.target.value)} className="w-4 h-4 text-blue-600" /> Não
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer text-black">
                    <input type="radio" name="medicacao" value="sim" checked={tomaMedicacao === 'sim'} onChange={(e) => setTomaMedicacao(e.target.value)} className="w-4 h-4 text-blue-600" /> Sim
                  </label>
                </div>
                {tomaMedicacao === 'sim' && (
                  <input type="text" required value={detalhesMedicacao} onChange={(e) => setDetalhesMedicacao(e.target.value)} placeholder="Qual medicação, frequência e horário? Ex: Ritalina, 1 comprimido às 08h" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none mt-2 text-black" />
                )}
              </div>

            </div>
          </section>

          {/* SESSÃO 4: Movimento */}
          <section>
            <h2 className="text-xl font-bold text-black mb-4 border-b border-gray-200 pb-2">4. Sobre o Movimento</h2>
            <div className="grid grid-cols-1 gap-5">
              <div>
                <label className="block text-sm font-bold text-black mb-2">Já conhecia o Movimento Escalada?</label>
                <select value={conheciaEscalada} onChange={(e) => setConheciaEscalada(e.target.value)} className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white text-black">
                  <option value="nao">Não, estou conhecendo agora</option>
                  <option value="sim">Sim, através de amigos/familiares</option>
                  <option value="redes_sociais">Sim, pelas redes sociais</option>
                  <option value="paroquia">Sim, por avisos na Paróquia</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-bold text-black mb-1">Faz parte de algum grupo pós-encontro? (Se aplicável)</label>
                <input type="text" value={grupoPosEncontro} onChange={(e) => setGrupoPosEncontro(e.target.value)} placeholder="Ex: Grupo de Jovens, Ministério de Música, Nenhum" className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-black" />
              </div>
            </div>
          </section>

          <div className="pt-6 border-t border-gray-200">
            <button type="submit" className="w-full py-4 bg-blue-600 text-white text-lg font-bold rounded-xl hover:bg-blue-700 transition-colors shadow-sm">
              Enviar Inscrição
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}