"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Lock, User } from 'lucide-react';

export default function Login() {
    const [usuario, setUsuario] = useState('');
    const [senha, setSenha] = useState('');
    const [erro, setErro] = useState('');
    const [carregando, setCarregando] = useState(false);
    
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault(); 
        setErro('');
        setCarregando(true);

        if (!usuario || !senha) {
            setErro('Por favor, preencha usuário e senha.');
            setCarregando(false);
            return;
        }

        try {
            const resposta = await fetch('http://localhost:8000/api/token/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    // 2. O Django exige que as chaves se chamem username e password
                    username: usuario, 
                    password: senha 
                }),
            });

            if (!resposta.ok) {
                const erroData = await resposta.json().catch(() => null);
                throw new Error(erroData?.detail || 'Usuário ou senha incorretos.');
            }

            const dados = await resposta.json();

            // 3. Verifica o nome do token retornado pelo Django (geralmente access ou access_token)
            // Salvamos o token em um Cookie que vale para todo o site (path=/)
            if (dados.access) {
                document.cookie = `sia_token=${dados.access}; path=/; max-age=86400`; // Expira em 1 dia
            } else if (dados.access_token) {
                document.cookie = `sia_token=${dados.access_token}; path=/; max-age=86400`;
            }

            router.push('/'); 

        } catch (error: any) {
            setErro(error.message || 'Ocorreu um erro ao conectar com o servidor.');
        } finally {
            setCarregando(false);
        }
    };

    return (
        <div className="w-full h-screen flex items-center justify-center bg-escalada-fundo p-4">
            <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden">
                
                <div className="bg-escalada-azul p-8 text-center flex flex-col items-center">
                    <div className="w-24 h-24 bg-white rounded-full flex items-center justify-center mb-4 shadow-inner">
                        <span className="text-escalada-vermelho font-bold text-2xl">SIA</span>
                    </div>
                    <h2 className="text-2xl font-bold text-white tracking-wide">Movimento Escalada de Brasília</h2>
                    <p className="text-blue-100 mt-1 text-sm">Sistema Integrado do Alpinista</p>
                </div>

                <div className="p-8">
                    <form onSubmit={handleLogin} className="space-y-6">

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Usuário</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <User className="h-5 w-5 text-gray-400" />
                                </div>
                                <input 
                                    type="text"
                                    value={usuario}
                                    onChange={(e) => setUsuario(e.target.value)}
                                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-escalada-azul focus:border-escalada-azul transition-colors outline-none"
                                    placeholder="Digite seu usuário"
                                    disabled={carregando}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Senha</label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-gray-400"/>
                                </div>
                                <input 
                                    type="password"
                                    value={senha}
                                    onChange={(e) => setSenha(e.target.value)}
                                    className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:ring-escalada-azul focus:border-escalada-azul transition-colors outline-none"
                                    placeholder="••••••••"
                                    disabled={carregando}
                                />
                            </div>
                            <div className="flex justify-end mt-2">
                                <a href="#" className="text-sm text-escalada-azul hover:underline font-medium">
                                    Esqueceu a Senha?
                                </a>
                            </div>
                        </div>

                        {erro && (
                            <div className="text-red-500 text-sm text-center font-medium">
                                {erro}
                            </div>
                        )}

                        <button 
                            type="submit"
                            disabled={carregando}
                            className={`w-full text-white font-bold py-3 px-4 rounded-lg transition-colors duration-200 shadow-md flex justify-center items-center gap-2 
                            ${carregando ? 'bg-gray-400 cursor-not-allowed' : 'bg-escalada-vermelho hover:bg-red-700'}`}
                        >
                            {carregando ? 'Entrando...' : 'Entrar no Sistema'}
                        </button>
                        
                    </form>
                </div>
            </div>
        </div>
    )
}