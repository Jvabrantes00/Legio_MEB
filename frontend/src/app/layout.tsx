import type {Metadata} from "next";
import {Inter} from "next/font/google";
import {Toaster} from 'react-hot-toast';
import "./globals.css";
import React from "react";
import { Tornado } from "lucide-react";

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
                <Toaster position = "bottom-right" reverseOrder={false} />
                {children}
            </body>
        </html>
    );
}