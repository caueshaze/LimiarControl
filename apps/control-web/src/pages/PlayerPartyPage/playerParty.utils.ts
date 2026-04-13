import type { ItemType } from "../../entities/item";
import type { Locale, LocaleKey } from "../../shared/i18n";
import type { PartyActiveSession, PartyMemberSummary } from "../../shared/api/partiesRepo";

type Translate = (key: LocaleKey) => string;

export const getLocaleCode = (locale: Locale) =>
  locale === "pt" ? "pt-BR" : "en-US";

export const formatPartyDate = (value: string, locale: Locale) =>
  new Intl.DateTimeFormat(getLocaleCode(locale), {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));

export const formatPartyDateTime = (value: string, locale: Locale) =>
  new Intl.DateTimeFormat(getLocaleCode(locale), {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));

export const formatOffset = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;

  if (hours > 0) {
    return `${hours}h${String(minutes).padStart(2, "0")}m`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
};

export const getPlayerPartyStatusKey = (
  status: PartyActiveSession["status"] | null | undefined,
): LocaleKey => {
  if (status === "ACTIVE") {
    return "playerParty.statusActive";
  }
  if (status === "LOBBY") {
    return "playerParty.statusLobby";
  }
  return "playerParty.statusIdle";
};

export const getSessionStatusLabel = (
  status: PartyActiveSession["status"],
  t: Translate,
) => {
  if (status === "ACTIVE") {
    return t("playerParty.sessionStatusActive");
  }
  if (status === "LOBBY") {
    return t("playerParty.sessionStatusLobby");
  }
  return t("playerParty.sessionStatusClosed");
};

export const getItemTypeLabel = (type: ItemType | undefined, t: Translate) => {
  switch (type) {
    case "WEAPON":
      return t("playerParty.itemTypeWeapon");
    case "ARMOR":
      return t("playerParty.itemTypeArmor");
    case "CONSUMABLE":
      return t("playerParty.itemTypeConsumable");
    case "MAGIC":
      return t("playerParty.itemTypeMagic");
    case "MISC":
      return t("playerParty.itemTypeMisc");
    default:
      return t("inventory.unknownType");
  }
};

export const getMemberBadgeLabel = (
  member: PartyMemberSummary,
  t: Translate,
) => {
  if (member.role === "GM") {
    return t("playerParty.memberRoleGm");
  }

  switch (member.status) {
    case "joined":
      return t("playerParty.memberStatusJoined");
    case "invited":
      return t("playerParty.memberStatusInvited");
    case "declined":
      return t("playerParty.memberStatusDeclined");
    case "left":
      return t("playerParty.memberStatusLeft");
    default:
      return t("playerParty.memberRolePlayer");
  }
};
