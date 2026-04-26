import type { SpellMapPreviewStatus } from "./spellMapPreviewModel";

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
    case "missing_position":
      return UNKNOWN_MESSAGE;
    default:
      return reason;
  }
};
