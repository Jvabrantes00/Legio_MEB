import type { EncontroSummary } from "../lib/sia-profile-contracts";

export function EncontroSummaryPanel({ encontro }: { encontro: EncontroSummary }) {
  return <div className="bg-white p-6 rounded-xl border border-gray-100">
    <h1 className="text-3xl font-bold">{encontro.encontro}</h1>
    <p className="text-gray-600 mt-2">Tipo: {encontro.tipo}</p>
    <p className="text-gray-600">Data de referência: {encontro.data_referencia}</p>
  </div>;
}
