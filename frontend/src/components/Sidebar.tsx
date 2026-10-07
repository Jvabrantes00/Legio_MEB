"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { LayoutDashboard, Users, Calendar, CalendarRange, LogOut, Menu, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { authMutation } from '../lib/sia-api';
import { useSiaSession } from './SiaSessionProvider';
import { siaNavigation } from '../lib/sia-navigation';
import { errorMessage, readApiError } from '../lib/form-api-error';

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const [mobileOpen, setMobileOpen] = useState(false);
    const { session, loading, error } = useSiaSession();

    const menuItems = siaNavigation(session);
    const icons = { '/': LayoutDashboard, '/alpinistas': Users, '/encontros': Calendar, '/calendario': CalendarRange };

    const handleLogout = async () => {
        try {
            const response = await authMutation('/api/auth/logout');
            if (!response.ok) {
                toast.error(await readApiError(response, 'Não foi possível encerrar a sessão.'));
                return;
            }
            router.push('/login');
            router.refresh();
        } catch (error: unknown) {
            toast.error(errorMessage(error, 'Não foi possível encerrar a sessão.'));
        }
    };

    const navigation = (mobile = false) => (
        <>
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
                            onClick={() => mobile && setMobileOpen(false)}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors duration-200 ${isAtivo ? 'bg-blue-800 text-white font-medium shadow-inner' : 'text-blue-100 hover:bg-blue-800 hover:text-white'}`}
                        >
                            <Icone size={20} className={isAtivo ? 'text-white' : 'text-blue-200'} />
                            <span className="font-medium">{item.nome}</span>
                        </Link>
                    );
                })}
            </nav>
            <div className="p-4 border-t border-blue-400/30">
                <button onClick={handleLogout} className="flex items-center gap-3 px-4 py-3 w-full rounded-lg hover:bg-red-500 transition-colors duration-200 text-sm font-medium">
                    <LogOut size={20} /><span>Sair</span>
                </button>
            </div>
        </>
    );

    return (
        <>
            <aside className="fixed left-0 top-0 z-40 hidden min-h-screen w-64 flex-col bg-escalada-azul text-white shadow-lg md:flex">
                <div className="p-6 border-b border-blue-400/30 flex items-center justify-center"><h1 className="text-2xl font-bold tracking-wider">SIA<span className="text-escalada-vermelho">.</span>MEB</h1></div>
                {navigation()}
            </aside>
            <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center justify-between bg-escalada-azul px-4 text-white shadow-lg md:hidden">
                <h1 className="text-xl font-bold tracking-wider">SIA<span className="text-escalada-vermelho">.</span>MEB</h1>
                <button type="button" onClick={() => setMobileOpen(true)} aria-label="Abrir navegação" aria-expanded={mobileOpen} className="rounded-lg p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"><Menu /></button>
            </header>
            {mobileOpen ? <div className="fixed inset-0 z-50 bg-slate-950/45 md:hidden" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setMobileOpen(false); }}>
                <aside className="flex h-full w-72 flex-col bg-escalada-azul text-white shadow-2xl" aria-label="Navegação principal">
                    <div className="flex items-center justify-between border-b border-blue-400/30 p-5"><h2 className="text-xl font-bold tracking-wider">SIA<span className="text-escalada-vermelho">.</span>MEB</h2><button type="button" onClick={() => setMobileOpen(false)} aria-label="Fechar navegação" className="rounded-lg p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"><X /></button></div>
                    {navigation(true)}
                </aside>
            </div> : null}
        </>
    );
}
