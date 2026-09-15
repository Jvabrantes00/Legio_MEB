import type { AlpinistaSummary } from "../lib/sia-profile-contracts";

function booleanLabel(value: boolean | null): string {
  return value === null ? "Não informado" : value ? "Sim" : "Não";
}

export function AlpinistaSummaryPanel({ profile }: { profile: AlpinistaSummary }) {
  return (
    <div className="space-y-4">
      <div className="bg-white p-5 rounded-xl border border-gray-100">
        <h3 className="font-semibold mb-3">Perfil resumido</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
          <div><dt className="text-gray-500">Idade</dt><dd>{profile.idade ?? "Não informada"}</dd></div>
          <div><dt className="text-gray-500">Grupo de pós-encontro</dt><dd>{profile.grupo || "Não informado"}</dd></div>
          <div><dt className="text-gray-500">WhatsApp</dt><dd>{profile.whatsapp || "Não informado"}</dd></div>
        </dl>
      </div>
      <div className="bg-white p-5 rounded-xl border border-gray-100">
        <h3 className="font-semibold mb-3">Situação sacramental</h3>
        <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div><dt className="text-gray-500">Batizado</dt><dd>{booleanLabel(profile.batizado)}</dd></div>
          <div><dt className="text-gray-500">Primeira comunhão</dt><dd>{booleanLabel(profile.primeira_comunhao)}</dd></div>
          <div><dt className="text-gray-500">Crismado</dt><dd>{booleanLabel(profile.crismado)}</dd></div>
        </dl>
      </div>
      <div className="bg-white p-5 rounded-xl border border-gray-100">
        <h3 className="font-semibold mb-3">Música</h3>
        <p className="text-sm">Violeiro: {profile.musica.violeiro ? "Sim" : "Não"} · Canta: {profile.musica.canta ? "Sim" : "Não"}</p>
      </div>
      {profile.responsaveis && profile.responsaveis.length > 0 && (
        <div className="bg-white p-5 rounded-xl border border-gray-100">
          <h3 className="font-semibold mb-3">Responsáveis</h3>
          <ul className="space-y-2 text-sm">
            {profile.responsaveis.map((responsavel, index) => (
              <li key={index}>{responsavel.nome || "Nome não informado"} · {responsavel.telefone || "Telefone não informado"}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
