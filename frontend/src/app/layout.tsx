import type {Metadata} from "next";
import {Inter} from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"]});

export const metadata: Metadata = {
    title: "SIA - Movimento Escalada de Brasília",
    description: "Sistema Integrado do Alpinista"
};

export default function RootLayout({
    children,
}: Readonly <{
    children: React.ReactNode;
}>) {
    return (
        <html lang="pt-BR">
            <body className={`${inter.className} bg-escalada-fundo text-escalada-texto min-h-screen`}>
                {children}
            </body>
        </html>
    );
}