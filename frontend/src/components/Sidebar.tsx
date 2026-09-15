// 1. A DIRETIVA 'USE CLIENT'
// No Next.js, os componentes nascem no "Servidor" por padrão.
// Usamos "use client" no topo para avisar: "Ei, este componente precisa interagir
// com o navegador (neste caso, ler a URL atual onde o usuário está)".
"use client";

import Link from 'next/link';
// 1. Importamos o useRouter para podermos navegar o usuário via código
import { usePathname, useRouter } from 'next/navigation'; 
import { LayoutDashboard, Users, Calendar, LogOut } from 'lucide-react';
import { authMutation } from '../lib/sia-api';
import { useSiaSession } from './SiaSessionProvider';
import { siaNavigation } from '../lib/sia-navigation';

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter(); // 2. Inicializamos o router
    const { session, loading, error } = useSiaSession();

    const menuItems = siaNavigation(session);
    const icons = { '/': LayoutDashboard, '/alpinistas': Users, '/encontros': Calendar };

    const handleLogout = async () => {
        const response = await authMutation('/api/auth/logout');
        if (response.ok) {
            router.push('/login');
            router.refresh();
        }
    };

    return (
        <aside className="w-64 bg-escalada-azul text-white min-h-screen flex flex-col shadow-lg fixed left-0 top-0">
            
            <div className="p-6 border-b border-blue-400/30 flex items-center justify-center">
                <h1 className="text-2xl font-bold tracking-wider">
                    SIA<span className="text-escalada-vermelho">.</span>MEB
                </h1>
            </div>

            <nav className="flex-1 px-4 py-6 space-y-2">
                {!loading && !error && menuItems.length === 0 && (
                    <p className="px-4 text-sm text-blue-100">Nenhum módulo disponível para seu papel.</p>
                )}
                {menuItems.map((item) => {
                    const Icone = icons[item.rota];
                    const isAtivo = item.rota === '/'
                        ? pathname === '/'
                        : pathname.startsWith(item.rota);
                    return (
                        <Link 
                            key={item.rota} 
                            href={item.rota}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200
                                ${isAtivo 
                                    ? 'bg-blue-800 text-white font-medium shadow-inner' 
                                    : 'text-blue-100 hover:bg-blue-800 hover:text-white' 
                                }`}
                        >
                            <Icone size={20} className={isAtivo ? 'text-white' : 'text-blue-200'} />
                            <span className="font-medium">{item.nome}</span>
                        </Link>
                    );
                })}
            </nav>

            <div className="p-4 border-t border-blue-400/30">
                {/* 4. Substituímos o console.log pela nossa nova função */}
                <button 
                    onClick={handleLogout}
                    className="flex items-center gap-3 px-4 py-3 w-full rounded-lg hover:bg-red-500 transition-colors duration-200 text-sm font-medium"
                >
                    <LogOut size={20} />
                    <span>Sair</span>
                </button>
            </div>
            
        </aside>
    );
}
