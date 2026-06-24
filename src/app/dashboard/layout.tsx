import Link from 'next/link';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex bg-slate-50">
      
      {/* Sidebar Fixa */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col shadow-xl z-10">
        <div className="p-6 text-2xl font-bold border-b border-slate-800">
          Escalada SIA
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2">
          <Link href="/dashboard" className="block px-4 py-2.5 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
            Painel Principal
          </Link>
          <Link href="/dashboard/alpinistas" className="block px-4 py-2.5 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
            Alpinistas
          </Link>
          <Link href="/dashboard/grupos" className="block px-4 py-2.5 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
            Grupos
          </Link>
          <Link href="/dashboard/eventos" className="block px-4 py-2.5 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-colors">
            Eventos e Frequência
          </Link>
        </nav>
        <div className="p-4 border-t border-slate-800">
          <Link href="/login" className="block px-4 py-2 text-sm text-slate-400 hover:text-white transition-colors">
            Sair do sistema
          </Link>
        </div>
      </aside>

      {/* O conteúdo dinâmico (Dashboard, Alpinistas, Grupos) vai renderizar aqui dentro: */}
      <main className="flex-1 p-8 overflow-y-auto">
        {children}
      </main>

    </div>
  );
}