import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Esta função roda toda vez que alguém tenta abrir qualquer página do seu site
export function proxy(request: NextRequest) {
    // 1. O guarda olha se existe um crachá (Cookie) válido
    const token = request.cookies.get('sia_token')?.value
    const urlAtual = request.nextUrl.pathname

    // 2. Se a pessoa já tem o crachá e tenta abrir a tela de Login, o sistema joga ela pro Dashboard
    if (urlAtual === '/login') {
        if (token) {
            return NextResponse.redirect(new URL('/', request.url))
        }
        return NextResponse.next()
    }

    // 3. Se a pessoa NÃO tem o crachá e tenta abrir qualquer página de dentro do sistema, é expulsa pro Login
    if (!token && request.nextUrl.pathname !== '/login') {
        return NextResponse.redirect(new URL('/login', request.url))
    }

    // 4. Se chegou até aqui, está tudo certo. Pode passar!
    return NextResponse.next()
}

// Configuração de onde o guarda deve ficar vigiando (ignoramos apenas imagens e arquivos do sistema)
export const config = {
    matcher: [
        '/dashboard/:path*', '/alpinista/:path*', '/encontros/:path*'
    ],
};