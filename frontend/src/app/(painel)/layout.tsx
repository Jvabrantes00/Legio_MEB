import Sidebar from "../../components/Sidebar";
import { SiaSessionProvider } from "../../components/SiaSessionProvider";

export default function PainelLayout({ children }: { children: React.ReactNode }) {
  return (
    <SiaSessionProvider><div className="min-h-screen bg-escalada-fundo">
      
      {/* 1. O Menu Fixo */}
      <Sidebar />

      {/* 2. O Contêiner Global
          'pl-64' cria um padding interno à esquerda de 256px (tamanho exato da sidebar).
          'w-full' garante que este bloco ocupe 100% da tela. */}
      <div className="w-full min-h-screen flex flex-col pt-16 md:pl-64 md:pt-0">
        
        {/* 3. A Área de Conteúdo 
            Como o padding segurou o espaço da esquerda, o conteúdo aqui dentro
            agora pode esticar com segurança usando o w-full. */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 w-full">
          {children}
        </main>
        
      </div>

    </div></SiaSessionProvider>
  );
}
