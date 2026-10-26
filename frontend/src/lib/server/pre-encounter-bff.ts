import { preEncounterMediaOperation } from "./pre-encounter-media";
import { preEncounterPdfKind } from "./pre-encounter-pdf";

const POSITIVE_INTEGER = /^[1-9]\d*$/;
const PHOTO_LOOKUP_QUERY_KEYS = new Set(["page", "q"]);

function isId(value: string | undefined): boolean {
  return Boolean(value && POSITIVE_INTEGER.test(value));
}

function hasOnlyPhotoLookupQuery(searchParams: URLSearchParams): boolean {
  for (const key of searchParams.keys()) {
    if (!PHOTO_LOOKUP_QUERY_KEYS.has(key) || searchParams.getAll(key).length !== 1) {
      return false;
    }
  }
  const page = searchParams.get("page");
  return page === null || isId(page);
}

export function isAllowedPreEncounterRequest(
  method: string,
  path: readonly string[],
  searchParams = new URLSearchParams(),
): boolean {
  if (preEncounterMediaOperation(method, path) !== null) return true;
  if (preEncounterPdfKind(method, path) !== null) return true;
  if (path[0] !== "encontros" || !isId(path[1]) || path[2] !== "pre-encontro") {
    return false;
  }

  const tail = path.slice(3);
  if (method === "GET") {
    return (
      (
        tail.length === 2
        && tail[0] === "fotos"
        && tail[1] === "atendimentos"
        && hasOnlyPhotoLookupQuery(searchParams)
      )
      ||
      (tail.length === 1 && (tail[0] === "atendimentos" || tail[0] === "capabilities"))
      || (
        tail.length === 2
        && tail[0] === "lookups"
        && (tail[1] === "inscricoes" || tail[1] === "pessoas")
      )
      || (tail.length === 2 && tail[0] === "atendimentos" && tail[1] === "busca")
      || (tail.length === 2 && tail[0] === "atendimentos" && isId(tail[1]))
      || (
        tail.length === 3
        && tail[0] === "atendimentos"
        && isId(tail[1])
        && tail[2] === "cuidados"
      )
      || (
        tail.length === 4
        && tail[0] === "atendimentos"
        && isId(tail[1])
        && tail[2] === "regularizacao"
        && (tail[3] === "inscricoes" || tail[3] === "pessoas")
      )
    );
  }
  if (method === "POST") {
    return (
      (tail.length === 1 && (
        tail[0] === "check-in"
        || tail[0] === "capacidade"
        || tail[0] === "configurar"
      ))
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
      && tail[2] === "pagamento"
    );
  }
  return false;
}
