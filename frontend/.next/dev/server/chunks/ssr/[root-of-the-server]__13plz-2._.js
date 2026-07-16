module.exports = [
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[project]/src/app/login/page.tsx [app-rsc] (ecmascript)", ((__turbopack_context__, module, exports) => {

// 3. A função que é disparada quando o formulário é enviado
const handleLogin = async (e)=>{
    e.preventDefault();
    setErro('');
    setCarregando(true);
    if (!usuario || !senha) {
        setErro('Por favor, preencha usuário e senha.');
        setCarregando(false);
        return;
    }
    try {
        // AQUI É A CONEXÃO REAL COM O SEU BACKEND
        // Substitua 'http://localhost:8000/login' pela rota exata da sua API
        const resposta = await fetch('http://localhost:8000/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            // Enviando os dados exatamente como o backend espera
            body: JSON.stringify({
                usuario: usuario,
                senha: senha
            })
        });
        // Se o backend retornar erro (ex: 401 Não Autorizado, 404 Não Encontrado)
        if (!resposta.ok) {
            // Tenta ler a mensagem de erro que o backend mandou
            const erroData = await resposta.json().catch(()=>null);
            throw new Error(erroData?.detail || 'Usuário ou senha incorretos.');
        }
        // Se passou do if acima, o login deu certo!
        const dados = await resposta.json();
        // Salva o token de acesso no navegador para as próximas requisições
        // O nome "access_token" depende de como você configurou no Python
        if (dados.access_token) {
            localStorage.setItem('sia_token', dados.access_token);
        }
        // Redireciona para o Painel
        router.push('/');
    } catch (error) {
        setErro(error.message || 'Ocorreu um erro ao conectar com o servidor.');
    } finally{
        setCarregando(false);
    }
};
}),
"[project]/src/app/login/page.tsx [app-rsc] (ecmascript, Next.js Server Component)", ((__turbopack_context__) => {

__turbopack_context__.n(__turbopack_context__.i("[project]/src/app/login/page.tsx [app-rsc] (ecmascript)"));
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__13plz-2._.js.map