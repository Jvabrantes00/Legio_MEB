import type { Metadata } from "next";

import { PublicInvitation } from "../../../components/PublicInvitation";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export const metadata: Metadata = {
  title: "Resposta ao convite — Movimento Escalada de Brasília",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default async function PublicInvitationPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <PublicInvitation token={token} />;
}
