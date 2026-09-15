export interface SiaSession {
  id: number;
  username: string;
  roles: string[];
  superuser: boolean;
}

const ADMIN_ROLES = new Set(["Suporte", "Diretoria", "Fichas"]);
const ENCOUNTER_READ_ROLES = new Set([...ADMIN_ROLES, "Comunicação"]);
const RECOGNIZED_ROLES = new Set([
  "Suporte", "Diretoria", "Fichas", "MME", "Formação", "Secretaria",
  "Ação Social", "Liturgia", "Eventos", "Comunicação",
]);

function hasRole(session: SiaSession | null, roles: Set<string>): boolean {
  return !!session && (session.superuser || session.roles.some((role) => roles.has(role)));
}

export function canViewAlpinistas(session: SiaSession | null): boolean {
  return hasRole(session, RECOGNIZED_ROLES);
}

export function canManageAlpinistas(session: SiaSession | null): boolean {
  return hasRole(session, ADMIN_ROLES);
}

export const canViewFullAlpinista = canManageAlpinistas;

export function canViewEncontros(session: SiaSession | null): boolean {
  return hasRole(session, ENCOUNTER_READ_ROLES);
}

export function canManageEncontros(session: SiaSession | null): boolean {
  return hasRole(session, ADMIN_ROLES);
}

export const canViewFullEncontro = canManageEncontros;
export const canManageEncontroParticipacoes = canManageEncontros;
export const canViewDashboard = canManageEncontros;

export function isSiaSession(value: unknown): value is SiaSession {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<SiaSession>;
  return typeof candidate.id === "number" && typeof candidate.username === "string" &&
    Array.isArray(candidate.roles) && candidate.roles.every((role) => typeof role === "string") &&
    typeof candidate.superuser === "boolean";
}
