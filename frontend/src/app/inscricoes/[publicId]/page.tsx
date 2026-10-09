import type { Metadata } from "next";
import { PublicRegistrationForm } from "../../../components/PublicRegistrationForm";

export const metadata: Metadata = {
  title: "Inscrição em Encontro — Movimento Escalada de Brasília",
  robots: { index: false, follow: false },
};

export default async function PublicRegistrationPage({ params }: { params: Promise<{ publicId: string }> }) {
  const { publicId } = await params;
  return <PublicRegistrationForm publicId={publicId} />;
}
