import type { SpellMapPreviewModel, SpellMapPreviewStatus } from "./spellMapPreviewModel";

const UNKNOWN_MESSAGE = "Dados de posição insuficientes para validar o preview no mapa";

export const formatSpellMapPreviewStatus = (status: SpellMapPreviewStatus): string => {
  switch (status) {
    case "valid":
      return "válido";
    case "invalid":
      return "inválido";
    case "partial":
      return "parcial";
    default:
      return "indisponível";
  }
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
      return "Origem da área: válida";
    case "invalid":
      return "Origem da área: inválida";
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
