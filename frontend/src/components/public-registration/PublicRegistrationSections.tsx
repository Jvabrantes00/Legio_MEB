import type { PublicRegistrationEncounter, PublicRegistrationErrors, PublicRegistrationValues } from "../../lib/public-registration-contract";
import { isMinorOnFirstOfficialDay } from "../../lib/public-registration-contract";
import { Field, RadioGroup, Section, SelectField, TextArea } from "./PublicRegistrationFields";

type Key = keyof PublicRegistrationValues;
interface Props {
  values: PublicRegistrationValues;
  errors: PublicRegistrationErrors;
  encounter: PublicRegistrationEncounter;
  change: (key: Key, value: string) => void;
}
const yesNo = [{ value: "sim", label: "Sim" }, { value: "nao", label: "Não" }] as const;
const sacraments = [{ value: "sim", label: "Sim" }, { value: "nao", label: "Não" }, { value: "nao_sei", label: "Não sei" }, { value: "nao_informado", label: "Não informado" }] as const;
const input = (props: Props, key: Key) => ({ value: props.values[key], onChange: (event: React.ChangeEvent<HTMLInputElement>) => props.change(key, event.target.value), error: props.errors[key] });
const area = (props: Props, key: Key) => ({ value: props.values[key], onChange: (event: React.ChangeEvent<HTMLTextAreaElement>) => props.change(key, event.target.value), error: props.errors[key] });
const select = (props: Props, key: Key) => ({ value: props.values[key], onChange: (event: React.ChangeEvent<HTMLSelectElement>) => props.change(key, event.target.value), error: props.errors[key] });

export function IdentificationSection(props: Props) {
  return <Section title="Identificação do participante">
    <Field id="nome_completo" label="Nome completo" required autoComplete="name" {...input(props, "nome_completo")} />
    <Field id="apelido" label="Apelido (opcional)" {...input(props, "apelido")} />
    <Field id="data_nascimento" label="Data de nascimento" required type="date" {...input(props, "data_nascimento")} />
    <Field id="cpf" label="CPF do participante (opcional)" inputMode="numeric" autoComplete="off" {...input(props, "cpf")} />
  </Section>;
}

export function ContactAddressSection(props: Props) {
  return <Section title="Contato e endereço" description="Informe pelo menos e-mail ou telefone/WhatsApp.">
    <Field id="email" label="E-mail" type="email" autoComplete="email" {...input(props, "email")} />
    <Field id="telefone_whatsapp" label="Telefone/WhatsApp" type="tel" autoComplete="tel" {...input(props, "telefone_whatsapp")} />
    <Field id="cep" label="CEP" required inputMode="numeric" placeholder="00000-000" autoComplete="postal-code" {...input(props, "cep")} />
    <Field id="logradouro" label="Logradouro" required autoComplete="address-line1" {...input(props, "logradouro")} />
    <Field id="numero" label="Número" required {...input(props, "numero")} />
    <Field id="complemento" label="Complemento (opcional)" autoComplete="address-line2" {...input(props, "complemento")} />
    <Field id="bairro" label="Bairro" required {...input(props, "bairro")} />
    <Field id="cidade" label="Cidade" required autoComplete="address-level2" {...input(props, "cidade")} />
    <Field id="uf" label="UF" required maxLength={2} autoComplete="address-level1" {...input(props, "uf")} />
  </Section>;
}

export function ResponsibleSection(props: Props) {
  const minor = isMinorOnFirstOfficialDay(props.values.data_nascimento, props.encounter);
  if (minor === null) return null;
  const legal = minor === true;
  return <Section title={legal ? "Responsável legal" : "Contato de emergência (opcional)"}
    description={legal ? "Obrigatório para quem tiver menos de 18 anos no primeiro dia oficial do Encontro." : "Se preencher algum dado, informe nome, relação e telefone. CPF e e-mail são opcionais."}>
    <Field id="responsavel_nome" label="Nome completo" required={legal} autoComplete="off" {...input(props, "responsavel_nome")} />
    <Field id="responsavel_cpf" label={legal ? "CPF" : "CPF (opcional)"} required={legal} inputMode="numeric" autoComplete="off" {...input(props, "responsavel_cpf")} />
    <Field id="responsavel_parentesco" label="Parentesco/relação" required={legal} {...input(props, "responsavel_parentesco")} />
    <Field id="responsavel_telefone" label="Telefone/WhatsApp" required={legal} type="tel" {...input(props, "responsavel_telefone")} />
    <Field id="responsavel_email" label="E-mail (opcional)" type="email" {...input(props, "responsavel_email")} />
  </Section>;
}

export function OriginSacramentsSection(props: Props) {
  return <Section title="Movimento e sacramentos">
    <div className="sm:col-span-2">
      <SelectField id="como_conheceu" label="Como conheceu o Movimento Escalada?" required
        options={[{ value: "indicacao", label: "Indicação de amigo/familiar" }, { value: "paroquia", label: "Paróquia" }, { value: "redes_sociais", label: "Redes sociais" }, { value: "ja_conhecia", label: "Já conhecia o Movimento Escalada" }, { value: "outro", label: "Outro" }]}
        {...select(props, "como_conheceu")} />
    </div>
    {props.values.como_conheceu === "outro" ? <Field id="como_conheceu_outro" label="Conte como conheceu" required {...input(props, "como_conheceu_outro")} /> : null}
    <div className="sm:col-span-2 grid gap-5 lg:grid-cols-3">
      {([['batismo', 'Batismo'], ['primeira_comunhao', 'Primeira Comunhão'], ['crisma', 'Crisma']] as const).map(([key, label]) =>
        <SelectField key={key} id={key} label={label} required options={sacraments} {...select(props, key)} />)}
    </div>
  </Section>;
}

export function CareSection(props: Props) {
  return <Section title="Informações importantes para cuidado e acolhimento" description="Estas informações ajudam a equipe a acolher e cuidar. Não são usadas para excluir automaticamente ninguém.">
    <RadioGroup legend="Possui alergias?" name="possui_alergias" value={props.values.possui_alergias} options={yesNo} onChange={(v) => props.change("possui_alergias", v)} error={props.errors.possui_alergias} />
    {props.values.possui_alergias === "sim" ? <TextArea id="alergias" label="Quais alergias?" required {...area(props, "alergias")} /> : <div />}
    <RadioGroup legend="Possui intolerância ou restrição alimentar?" name="possui_restricoes_intolerancias" value={props.values.possui_restricoes_intolerancias} options={yesNo} onChange={(v) => props.change("possui_restricoes_intolerancias", v)} error={props.errors.possui_restricoes_intolerancias} />
    {props.values.possui_restricoes_intolerancias === "sim" ? <TextArea id="restricoes_intolerancias" label="Quais restrições ou intolerâncias?" required {...area(props, "restricoes_intolerancias")} /> : <div />}
    <RadioGroup legend="Usa medicamentos?" name="usa_medicamentos" value={props.values.usa_medicamentos} options={yesNo} onChange={(v) => props.change("usa_medicamentos", v)} error={props.errors.usa_medicamentos} />
    {props.values.usa_medicamentos === "sim" ? <div className="space-y-5"><TextArea id="medicamentos" label="Medicamentos" required {...area(props, "medicamentos")} /><Field id="horarios_medicamentos" label="Horários" required {...input(props, "horarios_medicamentos")} /><TextArea id="observacoes_medicamentos" label="Observações (opcional)" {...area(props, "observacoes_medicamentos")} /></div> : <div />}
    <div className="sm:col-span-2"><RadioGroup legend="Existe neurodivergência, condição ou necessidade de apoio que a equipe deva conhecer?" name="neurodivergencia_apoio" value={props.values.neurodivergencia_apoio} options={[{ value: "sim", label: "Sim" }, { value: "nao", label: "Não" }, { value: "prefere_nao_informar", label: "Prefiro não informar" }]} onChange={(v) => props.change("neurodivergencia_apoio", v)} error={props.errors.neurodivergencia_apoio} /></div>
    {props.values.neurodivergencia_apoio === "sim" ? <>
      <TextArea id="neurodivergencia_condicao" label="Condição ou neurodivergência (opcional)" {...area(props, "neurodivergencia_condicao")} />
      <TextArea id="sensibilidades_desconfortos" label="Sensibilidades ou situações de desconforto (opcional)" {...area(props, "sensibilidades_desconfortos")} />
      <TextArea id="o_que_ajuda" label="O que costuma ajudar (opcional)" {...area(props, "o_que_ajuda")} />
      <TextArea id="necessidades_apoio" label="Necessidades de apoio (opcional)" {...area(props, "necessidades_apoio")} />
      <TextArea id="outras_informacoes" label="Outras informações relevantes (opcional)" {...area(props, "outras_informacoes")} />
    </> : null}
  </Section>;
}

export function EsppaSection(props: Props) {
  if (props.encounter.tipo !== "Esppa") return null;
  return <Section title="Informações específicas do ESPPA">
    <div className="sm:col-span-2"><RadioGroup legend="Estado civil" name="estado_civil" value={props.values.estado_civil} onChange={(v) => props.change("estado_civil", v)} error={props.errors.estado_civil}
      options={[{ value: "solteiro", label: "Solteiro(a)" }, { value: "casado", label: "Casado(a)" }, { value: "viuvo", label: "Viúvo(a)" }, { value: "divorciado", label: "Divorciado(a)" }]} /></div>
    {props.values.estado_civil === "casado" ? <>
      <Field id="nome_conjuge" label="Nome do cônjuge" required {...input(props, "nome_conjuge")} />
      <Field id="telefone_conjuge" label="Telefone do cônjuge" required type="tel" {...input(props, "telefone_conjuge")} />
    </> : props.values.estado_civil ? <>
      <Field id="nome_referencia" label="Nome da pessoa de referência" required {...input(props, "nome_referencia")} />
      <Field id="telefone_referencia" label="Telefone da pessoa de referência" required type="tel" {...input(props, "telefone_referencia")} />
      <div className="sm:col-span-2"><RadioGroup legend="Relação com a pessoa de referência" name="relacao_referencia" value={props.values.relacao_referencia} onChange={(v) => props.change("relacao_referencia", v)} error={props.errors.relacao_referencia}
        options={[{ value: "pai_mae", label: "Pai ou mãe" }, { value: "irmao_irma", label: "Irmão ou irmã" }, { value: "outro_familiar", label: "Outro familiar" }, { value: "amigo", label: "Amigo(a)" }, { value: "outro", label: "Outro" }]} /></div>
    </> : null}
  </Section>;
}
