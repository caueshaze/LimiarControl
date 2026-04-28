import type { AreaTargetSpatialMetadata, SpellCoverPreview, SpellMapPreviewModel, SpellMapPreviewStatus } from "./spellMapPreviewModel";

const UNKNOWN_MESSAGE = "Dados de posição insuficientes para validar o preview no mapa";

export const formatSpellMapPreviewStatus = (status: SpellMapPreviewStatus): string => {
  switch (status) {
    case "valid":
      return "livre";
    case "invalid":
      return "bloqueado";
    case "partial":
      return "parcial";
    default:
      return "indisponível";
  }
};

export type SpellCoverContext = "attack" | "save" | "other";

export const resolveCoverContext = (
  spellMode: string | null | undefined,
  coverAppliesToSave?: boolean | null,
): SpellCoverContext => {
  if (spellMode === "spell_attack") return "attack";
  if (spellMode === "saving_throw" && coverAppliesToSave === true) return "save";
  return "other";
};

export const formatSpellCoverPreview = (
  cover: SpellCoverPreview | null | undefined,
  context: SpellCoverContext,
): string | null => {
  if (!cover || cover.rank === "none" || cover.rank === "unknown") return null;
  if (context === "other") return null;
  const rankLabel = cover.rank === "half" ? "meia cobertura" : "três-quartos";
  const modifier = cover.bonus ?? 0;
  if (context === "attack") return `Cobertura: ${rankLabel} (+${modifier} AC)`;
  if (context === "save") return `Cobertura: ${rankLabel} (-${modifier} DC efetiva)`;
  return null;
};

export const formatAreaOriginPreviewLabel = (
  model: Pick<SpellMapPreviewModel, "status" | "reason">,
): string => {
  switch (model.reason) {
    case "out_of_range":
      return "Origem da área: fora do alcance";
    case "blocked_line_of_sight":
      return "Origem da área: linha de visão bloqueada";
    case "blocked_line_of_effect":
      return "Origem da área: linha de efeito bloqueada";
    case "missing_position":
      return "Origem da área: dados de posição insuficientes";
    case "missing_map_data":
      return "Origem da área: dados do mapa insuficientes";
    default:
      break;
  }
  switch (model.status) {
    case "valid":
      return "Origem da área: livre";
    case "invalid":
      return "Origem da área: bloqueada";
    case "unknown":
      return "Origem da área: dados insuficientes";
    default:
      return "Origem da área: indisponível";
  }
};

export const formatSpellMapPreviewReason = (
  reason?: string | null,
  status?: SpellMapPreviewStatus,
): string | null => {
  if (!reason) {
    return status === "unknown" ? UNKNOWN_MESSAGE : null;
  }

  switch (reason) {
    case "out_of_range":
      return "fora do alcance";
    case "blocked_line_of_sight":
      return "linha de visão bloqueada";
    case "blocked_line_of_effect":
      return "linha de efeito bloqueada";
    case "missing_position":
      return "dados de posição insuficientes";
    case "missing_map_data":
      return "dados do mapa insuficientes";
    default:
      return reason;
  }
};

export const formatAreaTargetCoverRank = (cover: string | null | undefined): string | null => {
  if (cover === "half") return "meia cobertura";
  if (cover === "three_quarters" || cover === "threeQuarters") return "três-quartos";
  return null;
};

export const formatAreaTargetEffectiveDcLine = (
  item: AreaTargetSpatialMetadata,
): string | null => {
  const dc = item.effectiveSaveDc ?? item.baseSaveDc;
  if (dc == null) return null;

  const name = item.targetDisplayName ?? item.targetRefId;
  const coverLabel =
    item.coverModifier > 0 ? formatAreaTargetCoverRank(item.cover) : null;

  if (coverLabel) {
    return `${name}: ${coverLabel}, DC efetiva ${dc}`;
  }
  return `${name}: DC ${dc}`;
};

export const formatTargetList = (names: string[], max = 5): string => {
  if (names.length <= max) return names.join(", ");
  const visible = names.slice(0, max);
  const hiddenCount = names.length - max;
  return `${visible.join(", ")} +${hiddenCount} outros`;
};
