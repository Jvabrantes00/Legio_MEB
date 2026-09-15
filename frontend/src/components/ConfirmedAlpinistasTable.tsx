import type { ConfirmedAlpinista } from "../lib/sia-profile-contracts";

interface Props {
  people: ConfirmedAlpinista[];
  selected: number[];
  toggle: (id: number) => void;
}

export function ConfirmedAlpinistasTable({ people, selected, toggle }: Props) {
  return <div className="overflow-x-auto border border-gray-200 rounded-xl">
    <table className="w-full text-left">
      <thead className="bg-gray-50 border-b border-gray-200 text-sm text-gray-500 uppercase">
        <tr><th className="px-4 py-3 w-10 text-center">Selecionar</th><th className="px-4 py-3 font-semibold">Nome</th></tr>
      </thead>
      <tbody className="divide-y divide-gray-100">
        {people.map((person) => <tr key={person.id} className="hover:bg-red-50/50 transition-colors cursor-pointer" onClick={() => toggle(person.id)}>
          <td className="px-4 py-4 text-center">
            <input type="checkbox" checked={selected.includes(person.id)} onChange={() => toggle(person.id)} onClick={(event) => event.stopPropagation()} aria-label={`Selecionar ${person.nome}`} />
          </td>
          <td className="px-4 py-4 font-medium text-gray-900">{person.nome}</td>
        </tr>)}
      </tbody>
    </table>
  </div>;
}
