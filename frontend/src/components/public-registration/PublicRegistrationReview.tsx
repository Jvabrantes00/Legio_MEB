import type { PublicRegistrationEncounter, PublicRegistrationValues } from "../../lib/public-registration-contract";
import { isMinorOnFirstOfficialDay } from "../../lib/public-registration-contract";

const labels: Partial<Record<keyof PublicRegistrationValues, string>> = {
  nome_completo: "Nome completo", apelido: "Apelido", data_nascimento: "Data de nascimento", cpf: "CPF do participante",
  email: "E-mail", telefone_whatsapp: "Telefone/WhatsApp", cep: "CEP", logradouro: "Logradouro", numero: "Número",
  complemento: "Complemento", bairro: "Bairro", cidade: "Cidade", uf: "UF", como_conheceu: "Como conheceu",
  como_conheceu_outro: "Detalhe", batismo: "Batismo", primeira_comunhao: "Primeira Comunhão", crisma: "Crisma",
  responsavel_nome: "Nome", responsavel_cpf: "CPF", responsavel_parentesco: "Parentesco/relação", responsavel_telefone: "Telefone", responsavel_email: "E-mail",
  possui_alergias: "Possui alergias", alergias: "Alergias", possui_restricoes_intolerancias: "Possui restrições/intolerâncias",
  restricoes_intolerancias: "Restrições/intolerâncias", usa_medicamentos: "Usa medicamentos", medicamentos: "Medicamentos",
  horarios_medicamentos: "Horários", observacoes_medicamentos: "Observações", neurodivergencia_apoio: "Condição ou necessidade de apoio",
  neurodivergencia_condicao: "Condição/neurodivergência", necessidades_apoio: "Necessidades de apoio",
  sensibilidades_desconfortos: "Sensibilidades/desconfortos", o_que_ajuda: "O que ajuda", outras_informacoes: "Outras informações",
  estado_civil: "Estado civil", nome_conjuge: "Nome do cônjuge", telefone_conjuge: "Telefone do cônjuge",
  nome_referencia: "Pessoa de referência", relacao_referencia: "Relação", telefone_referencia: "Telefone da referência",
};
const valueLabels: Record<string, string> = {
  sim: "Sim", nao: "Não", nao_sei: "Não sei", nao_informado: "Não informado", prefere_nao_informar: "Prefiro não informar",
  indicacao: "Indicação de amigo/familiar", paroquia: "Paróquia", redes_sociais: "Redes sociais", ja_conhecia: "Já conhecia o Movimento Escalada", outro: "Outro",
  solteiro: "Solteiro(a)", casado: "Casado(a)", viuvo: "Viúvo(a)", divorciado: "Divorciado(a)", pai_mae: "Pai ou mãe",
  irmao_irma: "Irmão ou irmã", outro_familiar: "Outro familiar", amigo: "Amigo(a)",
};

function ReviewSection({ title, values, fields }: { title: string; values: PublicRegistrationValues; fields: (keyof PublicRegistrationValues)[] }) {
  const visible = fields.filter((field) => values[field].trim());
  if (!visible.length) return null;
  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
    <h2 className="text-lg font-bold text-slate-900">{title}</h2>
    <dl className="mt-4 grid gap-4 sm:grid-cols-2">
      {visible.map((field) => <div key={field}><dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{labels[field]}</dt><dd className="mt-1 whitespace-pre-wrap text-sm text-slate-900">{valueLabels[values[field]] ?? values[field]}</dd></div>)}
    </dl>
  </section>;
}

export function PublicRegistrationReview({ values, encounter }: { values: PublicRegistrationValues; encounter: PublicRegistrationEncounter }) {
  const minor = isMinorOnFirstOfficialDay(values.data_nascimento, encounter);
  return <div className="space-y-5" data-testid="registration-review">
    <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5"><h2 className="text-xl font-bold text-blue-950">Revise antes de enviar</h2><p className="mt-1 text-sm text-blue-900">A inscrição só será criada quando você confirmar no final desta página.</p></div>
    <ReviewSection title="Identificação" values={values} fields={["nome_completo", "apelido", "data_nascimento", "cpf"]} />
    <ReviewSection title="Contato e endereço" values={values} fields={["email", "telefone_whatsapp", "cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf"]} />
    <ReviewSection title={minor ? "Responsável legal" : "Contato de emergência"} values={values} fields={["responsavel_nome", "responsavel_cpf", "responsavel_parentesco", "responsavel_telefone", "responsavel_email"]} />
    <ReviewSection title="Movimento e sacramentos" values={values} fields={["como_conheceu", "como_conheceu_outro", "batismo", "primeira_comunhao", "crisma"]} />
    <ReviewSection title="Cuidado e acolhimento" values={values} fields={["possui_alergias", "alergias", "possui_restricoes_intolerancias", "restricoes_intolerancias", "usa_medicamentos", "medicamentos", "horarios_medicamentos", "observacoes_medicamentos", "neurodivergencia_apoio", "neurodivergencia_condicao", "sensibilidades_desconfortos", "o_que_ajuda", "necessidades_apoio", "outras_informacoes"]} />
    {encounter.tipo === "Esppa" ? <ReviewSection title="Informações do ESPPA" values={values} fields={["estado_civil", "nome_conjuge", "telefone_conjuge", "nome_referencia", "relacao_referencia", "telefone_referencia"]} /> : null}
  </div>;
}
