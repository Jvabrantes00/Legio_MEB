const POSITIVE_INTEGER = /^[1-9]\d*$/;

function isId(value: string | undefined): boolean {
  return Boolean(value && POSITIVE_INTEGER.test(value));
}

export function isAllowedPreEncounterRequest(
  method: string,
  path: readonly string[],
): boolean {
  if (path[0] !== "encontros" || !isId(path[1]) || path[2] !== "pre-encontro") {
    return false;
  }

  const tail = path.slice(3);
  if (method === "GET") {
    return (
      (tail.length === 1 && (tail[0] === "atendimentos" || tail[0] === "capabilities"))
      || (tail.length === 2 && tail[0] === "atendimentos" && tail[1] === "busca")
      || (tail.length === 2 && tail[0] === "atendimentos" && isId(tail[1]))
      || (
        tail.length === 3
        && tail[0] === "atendimentos"
        && isId(tail[1])
        && (tail[2] === "cuidados" || tail[2] === "foto")
      )
    );
  }
  if (method === "POST") {
    return (
      (tail.length === 1 && (tail[0] === "check-in" || tail[0] === "capacidade"))
      || (
        tail.length === 3
        && tail[0] === "atendimentos"
        && isId(tail[1])
        && (tail[2] === "regularizar" || tail[2] === "decisao-vaga")
      )
      || (
        tail.length === 4
        && tail[0] === "atendimentos"
        && isId(tail[1])
        && tail[2] === "cuidados"
        && tail[3] === "conferir"
      )
    );
  }
  if (method === "PUT") {
    return (
      tail.length === 3
      && tail[0] === "atendimentos"
      && isId(tail[1])
      && (tail[2] === "pagamento" || tail[2] === "foto")
    );
  }
  return false;
}
