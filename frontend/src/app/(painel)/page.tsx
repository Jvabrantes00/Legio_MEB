import { Users, CalendarDays, Activity, ArrowRight } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="space-y-8 animate-fade-in">
      
      {/* Cabeçalho da Página */}
      <div>
        {/* Usando o seu nome aqui para simular o usuário logado */}
        <h1 className="text-3xl font-bold text-escalada-texto">Bem-vindo, Vinicius Prado!</h1>
        <p className="text-gray-500 mt-1">Aqui está o panorama atual do Movimento Escalada.</p>
      </div>

      {/* Grid de Cards de Resumo */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Card 1: Total de Alpinistas */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
          <div className="p-4 bg-blue-50 text-escalada-azul rounded-xl">
            <Users className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total de Alpinistas</p>
            <h3 className="text-2xl font-bold text-escalada-texto">1.248</h3>
          </div>
        </div>
        
        {/* Card 2: Próximo Encontro */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
          <div className="p-4 bg-red-50 text-escalada-vermelho rounded-xl">
            <CalendarDays className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Próximo Encontro</p>
            <h3 className="text-2xl font-bold text-escalada-texto">Em 15 Dias</h3>
          </div>
        </div>

        {/* Card 3: Atividade Recente */}
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex items-center space-x-4 hover:shadow-md transition-shadow">
          <div className="p-4 bg-green-50 text-green-600 rounded-xl">
            <Activity className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Novas Inscrições (Mês)</p>
            <h3 className="text-2xl font-bold text-escalada-texto">+24</h3>
          </div>
        </div>
        
      </div>

      {/* Seção de Últimas Atividades (Tabela) */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-lg font-bold text-escalada-texto">Últimas Inscrições</h2>
          <button className="text-sm text-escalada-azul hover:underline flex items-center gap-1 font-medium">
            Ver todas <ArrowRight className="w-4 h-4" />
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="bg-gray-50 text-gray-500 text-sm">
              <tr>
                <th className="px-6 py-4 font-medium">Nome</th>
                <th className="px-6 py-4 font-medium">Data da Inscrição</th>
                <th className="px-6 py-4 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-sm">
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-escalada-texto">Maria Silva</td>
                <td className="px-6 py-4 text-gray-500">Hoje, 14:30</td>
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold tracking-wide">CONFIRMADA</span>
                </td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-escalada-texto">João Pedro de Souza</td>
                <td className="px-6 py-4 text-gray-500">Ontem, 09:15</td>
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-xs font-bold tracking-wide">PENDENTE</span>
                </td>
              </tr>
              <tr className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4 font-medium text-escalada-texto">Ana Beatriz</td>
                <td className="px-6 py-4 text-gray-500">13 Jul 2026</td>
                <td className="px-6 py-4">
                  <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold tracking-wide">EM ANÁLISE</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
      
    </div>
  );
}