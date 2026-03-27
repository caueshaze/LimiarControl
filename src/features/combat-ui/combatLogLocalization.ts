import type { Locale } from "../../shared/i18n";

type LocalizedToken = {
  en: string;
  pt: string;
  variants?: string[];
};

const DAMAGE_TOKENS: LocalizedToken[] = [
  { en: "Acid", pt: "Ácido", variants: ["acid", "acido", "ácido"] },
  { en: "Bludgeoning", pt: "Contundente", variants: ["bludgeoning", "contundente"] },
  { en: "Cold", pt: "Frio", variants: ["cold", "frio"] },
  { en: "Fire", pt: "Fogo", variants: ["fire", "fogo"] },
  { en: "Force", pt: "Força", variants: ["force", "forca", "força"] },
  { en: "Lightning", pt: "Elétrico", variants: ["lightning", "eletrico", "elétrico"] },
  { en: "Necrotic", pt: "Necrótico", variants: ["necrotic", "necrotico", "necrótico"] },
  { en: "Piercing", pt: "Perfurante", variants: ["piercing", "perfurante"] },
  { en: "Poison", pt: "Veneno", variants: ["poison", "veneno"] },
  { en: "Psychic", pt: "Psíquico", variants: ["psychic", "psiquico", "psíquico"] },
  { en: "Radiant", pt: "Radiante", variants: ["radiant", "radiante"] },
  { en: "Slashing", pt: "Cortante", variants: ["slashing", "cortante"] },
  { en: "Thunder", pt: "Trovão", variants: ["thunder", "trovao", "trovão"] },
] as const;

const EFFECT_TOKENS: LocalizedToken[] = [
  { en: "prone", pt: "caído no chão", variants: ["prone", "caido no chao", "caído no chão"] },
  { en: "poisoned", pt: "envenenado", variants: ["poisoned", "envenenado"] },
  { en: "restrained", pt: "contido", variants: ["restrained", "contido"] },
  { en: "blinded", pt: "cego", variants: ["blinded", "cego"] },
  { en: "frightened", pt: "amedrontado", variants: ["frightened", "amedrontado"] },
  { en: "temp_ac_bonus", pt: "bônus de CA", variants: ["temp_ac_bonus", "bonus de ca", "bônus de ca"] },
  { en: "attack_bonus", pt: "bônus de ataque", variants: ["attack_bonus", "bonus de ataque", "bônus de ataque"] },
  { en: "damage_bonus", pt: "bônus de dano", variants: ["damage_bonus", "bonus de dano", "bônus de dano"] },
  {
    en: "advantage_on_attacks",
    pt: "vantagem em ataques",
    variants: ["advantage_on_attacks", "vantagem em ataques"],
  },
  {
    en: "disadvantage_on_attacks",
    pt: "desvantagem em ataques",
    variants: ["disadvantage_on_attacks", "desvantagem em ataques"],
  },
  { en: "dodging", pt: "esquivando", variants: ["dodging", "esquivando"] },
  { en: "hidden", pt: "escondido", variants: ["hidden", "escondido"] },
] as const;

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const replaceTokenSet = (message: string, locale: Locale, tokens: readonly LocalizedToken[]) =>
  tokens.reduce((current, token) => {
    const variants = token.variants ?? [token.en, token.pt];
    const replacement = locale === "pt" ? token.pt : token.en;
    return variants.reduce(
      (value, variant) => value.replace(new RegExp(`\\b${escapeRegExp(variant)}\\b`, "gi"), replacement),
      current,
    );
  }, message);

const normalizeCombatTail = (tail: string, locale: Locale) => {
  let value = tail;

  if (locale === "pt") {
    value = value
      .replace(/\. Damage roll pending\./gi, ". Dano pendente.")
      .replace(/ Damage roll pending\./gi, " Dano pendente.")
      .replace(/ Effect pending\./gi, " Efeito pendente.")
      .replace(/ Healing pending\./gi, " Cura pendente.")
      .replace(/ and took no damage/gi, " e nao sofreu dano")
      .replace(/ and took half damage: (\d+) ([A-Za-zÀ-ÿ_]+) damage \(rolled (\d+)\)/gi, (_match, amount, type, rolled) =>
        ` e sofreu metade do dano: ${amount} de dano ${replaceTokenSet(type, "pt", DAMAGE_TOKENS)} (rolado ${rolled})`,
      )
      .replace(/ and took (\d+) ([A-Za-zÀ-ÿ_]+) damage/gi, (_match, amount, type) =>
        ` e sofreu ${amount} de dano ${replaceTokenSet(type, "pt", DAMAGE_TOKENS)}`,
      )
      .replace(/ for (\d+) ([A-Za-zÀ-ÿ_]+) damage/gi, (_match, amount, type) =>
        ` ${amount} de dano ${replaceTokenSet(type, "pt", DAMAGE_TOKENS)}`,
      )
      .replace(/ for (\d+) damage/gi, (_match, amount) => ` ${amount} de dano`)
      .replace(/\(DEFEATED!\)/gi, "(Derrotado!)")
      .replace(/\(Fell unconscious!\)/gi, "(Caiu inconsciente!)")
      .replace(/\(Revived!\)/gi, "(Reviveu!)")
      .replace(/\(Took damage while downed and DIED!\)/gi, "(Sofreu dano caído e MORREU!)")
      .replace(/\(Took damage while downed! \+(\d+) failure\(s\)\)/gi, (_match, amount) =>
        `(Sofreu dano caído! +${amount} falha(s))`,
      );
  } else {
    value = value
      .replace(/\. Dano pendente\./gi, ". Damage roll pending.")
      .replace(/ Dano pendente\./gi, " Damage roll pending.")
      .replace(/ Efeito pendente\./gi, " Effect pending.")
      .replace(/ Cura pendente\./gi, " Healing pending.")
      .replace(/ e nao sofreu dano/gi, " and took no damage")
      .replace(/ e sofreu metade do dano: (\d+) de dano (?:de )?([A-Za-zÀ-ÿ_]+) \(rolado (\d+)\)/gi, (_match, amount, type, rolled) =>
        ` and took half damage: ${amount} ${replaceTokenSet(type, "en", DAMAGE_TOKENS)} damage (rolled ${rolled})`,
      )
      .replace(/ e sofreu (\d+) de dano (?:de )?([A-Za-zÀ-ÿ_]+)/gi, (_match, amount, type) =>
        ` and took ${amount} ${replaceTokenSet(type, "en", DAMAGE_TOKENS)} damage`,
      )
      .replace(/ (\d+) de dano (?:de )?([A-Za-zÀ-ÿ_]+)/gi, (_match, amount, type) =>
        ` ${amount} ${replaceTokenSet(type, "en", DAMAGE_TOKENS)} damage`,
      )
      .replace(/ (\d+) de dano/gi, (_match, amount) => ` ${amount} damage`)
      .replace(/\(Derrotado!\)/gi, "(DEFEATED!)")
      .replace(/\(Caiu inconsciente!\)/gi, "(Fell unconscious!)")
      .replace(/\(Reviveu!\)/gi, "(Revived!)")
      .replace(/\(Sofreu dano caído e MORREU!\)/gi, "(Took damage while downed and DIED!)")
      .replace(/\(Sofreu dano caído! \+(\d+) falha\(s\)\)/gi, (_match, amount) =>
        `(Took damage while downed! +${amount} failure(s))`,
      );
  }

  return replaceTokenSet(replaceTokenSet(value, locale, DAMAGE_TOKENS), locale, EFFECT_TOKENS);
};

const localizeKnownEnglishMessage = (message: string, locale: Locale) => {
  if (locale !== "pt") {
    return message;
  }

  let match = message.match(/^Initiative set! It is now (.+?)'s turn\.$/i);
  if (match) {
    return `Iniciativa definida! Agora e o turno de ${match[1]}.`;
  }

  match = message.match(/^Round (\d+) started!$/i);
  if (match) {
    return `Rodada ${match[1]} comecou!`;
  }

  match = message.match(/^Turn skipped for stable participant (.+?)\.$/i);
  if (match) {
    return `Turno pulado para o participante estavel ${match[1]}.`;
  }

  match = message.match(/^It is now (.+?)'s turn\. They are downed and must roll a Death Save\.$/i);
  if (match) {
    return `Agora e o turno de ${match[1]}. Esta caido e precisa rolar um teste de morte.`;
  }

  match = message.match(/^It is now (.+?)'s turn\.$/i);
  if (match) {
    return `Agora e o turno de ${match[1]}.`;
  }

  match = message.match(/^Effect '(.+?)' applied to (.+?)\.$/i);
  if (match) {
    return `Efeito '${replaceTokenSet(match[1], "pt", EFFECT_TOKENS)}' aplicado em ${match[2]}.`;
  }

  match = message.match(/^Effect '(.+?)' removed from (.+?)\.$/i);
  if (match) {
    return `Efeito '${replaceTokenSet(match[1], "pt", EFFECT_TOKENS)}' removido de ${match[2]}.`;
  }

  match = message.match(/^Effect '(.+?)' expired on (.+?) \((end|start) of (.+?)'s turn\)\.$/i);
  if (match) {
    const when = match[3].toLowerCase() === "end" ? "fim" : "inicio";
    return `Efeito '${replaceTokenSet(match[1], "pt", EFFECT_TOKENS)}' expirou em ${match[2]} (${when} do turno de ${match[4]}).`;
  }

  match = message.match(/^(.+?) used their reaction\.$/i);
  if (match) {
    return `${match[1]} usou a propria reacao.`;
  }

  match = message.match(/^(.+?) takes the Dodge action\.$/i);
  if (match) {
    return `${match[1]} usa a acao Esquivar.`;
  }

  match = message.match(/^(.+?) helps (.+?) with their next attack\.$/i);
  if (match) {
    return `${match[1]} ajuda ${match[2]} no proximo ataque.`;
  }

  match = message.match(/^(.+?) attempts to hide \(Stealth: (\d+)\)\.$/i);
  if (match) {
    return `${match[1]} tenta se esconder (Furtividade: ${match[2]}).`;
  }

  match = message.match(/^(.+?) uses (.+?)\.$/i);
  if (match) {
    const description = match[2].toLowerCase() === "an object" ? "um objeto" : match[2];
    return `${match[1]} usa ${description}.`;
  }

  match = message.match(/^(.+?) takes the Dash action\.$/i);
  if (match) {
    return `${match[1]} usa a acao Disparada.`;
  }

  match = message.match(/^(.+?) takes the Disengage action\.$/i);
  if (match) {
    return `${match[1]} usa a acao Desengajar.`;
  }

  match = message.match(/^GM applied (\d+) damage\.(.*)$/i);
  if (match) {
    return `GM aplicou ${match[1]} de dano.${normalizeCombatTail(match[2], "pt")}`;
  }

  match = message.match(/^GM applied (\d+) healing\.(.*)$/i);
  if (match) {
    return `GM aplicou ${match[1]} de cura.${normalizeCombatTail(match[2], "pt")}`;
  }

  match = message.match(/^(.+?) (HIT|MISSED|CRITICALLY HIT|CRITICALLY MISSED) (.+?) \(AC (\d+)\) with (.+?) and roll (\d+)\.(.*)$/i);
  if (match) {
    const outcomeMap: Record<string, string> = {
      HIT: "acertou",
      MISSED: "errou",
      "CRITICALLY HIT": "acertou criticamente",
      "CRITICALLY MISSED": "errou criticamente",
    };
    return `${match[1]} ${outcomeMap[match[2].toUpperCase()] ?? "agiu contra"} ${match[3]} (CA ${match[4]}) com ${match[5]} e rolagem ${match[6]}.${normalizeCombatTail(match[7], "pt")}`;
  }

  match = message.match(/^(.+?) rolled damage with (.+?) against (.+?): (\d+) damage\.(.*)$/i);
  if (match) {
    return `${match[1]} rolou dano com ${match[2]} contra ${match[3]}: ${match[4]} de dano.${normalizeCombatTail(match[5], "pt")}`;
  }

  match = message.match(/^(.+?) used (.+?) on (.+?): (HIT|MISSED|CRITICALLY HIT|CRITICALLY MISSED) \(roll (\d+)\)(.*)$/i);
  if (match) {
    const outcomeMap: Record<string, string> = {
      HIT: "acerto",
      MISSED: "erro",
      "CRITICALLY HIT": "acerto critico",
      "CRITICALLY MISSED": "erro critico",
    };
    return `${match[1]} usou ${match[2]} em ${match[3]}: ${outcomeMap[match[4].toUpperCase()] ?? match[4].toLowerCase()} (rolagem ${match[5]})${normalizeCombatTail(match[6], "pt")}`;
  }

  match = message.match(/^(.+?) used (.+?) on (.+?): (.+?) (SUCCEEDED|FAILED) the (.+?) save \((\d+) vs DC (\d+)\)(.*)$/i);
  if (match) {
    const outcome = match[5].toUpperCase() === "SUCCEEDED" ? "passou" : "falhou";
    return `${match[1]} usou ${match[2]} em ${match[3]}: ${match[4]} ${outcome} no teste de ${match[6]} (${match[7]} vs CD ${match[8]})${normalizeCombatTail(match[9], "pt")}`;
  }

  match = message.match(/^(.+?) used (.+?) on (.+?), healing (\d+) HP(.*)$/i);
  if (match) {
    return `${match[1]} usou ${match[2]} em ${match[3]}, restaurando ${match[4]} PV${normalizeCombatTail(match[5], "pt")}`;
  }

  match = message.match(/^(.+?) used (.+?)\.(.*)$/i);
  if (match) {
    return `${match[1]} usou ${match[2]}.${normalizeCombatTail(match[3], "pt")}`;
  }

  if (message === "Combat started! Roll for initiative.") {
    return "Combate iniciado! Role a iniciativa.";
  }
  if (message === "Combat ended.") {
    return "Combate encerrado.";
  }
  if (message === "Initiative updated.") {
    return "Iniciativa atualizada.";
  }

  return replaceTokenSet(replaceTokenSet(message, "pt", DAMAGE_TOKENS), "pt", EFFECT_TOKENS);
};

const localizeKnownPortugueseMessage = (message: string, locale: Locale) => {
  if (locale !== "en") {
    return message;
  }

  let match = message.match(/^Iniciativa definida! Agora e o turno de (.+?)\.$/i);
  if (match) {
    return `Initiative set! It is now ${match[1]}'s turn.`;
  }

  match = message.match(/^Rodada (\d+) comecou!$/i);
  if (match) {
    return `Round ${match[1]} started!`;
  }

  match = message.match(/^Turno pulado para o participante estavel (.+?)\.$/i);
  if (match) {
    return `Turn skipped for stable participant ${match[1]}.`;
  }

  match = message.match(/^Agora e o turno de (.+?)\. Esta caido e precisa rolar um teste de morte\.$/i);
  if (match) {
    return `It is now ${match[1]}'s turn. They are downed and must roll a Death Save.`;
  }

  match = message.match(/^Agora e o turno de (.+?)\.$/i);
  if (match) {
    return `It is now ${match[1]}'s turn.`;
  }

  match = message.match(/^Efeito '(.+?)' aplicado em (.+?)\.$/i);
  if (match) {
    return `Effect '${replaceTokenSet(match[1], "en", EFFECT_TOKENS)}' applied to ${match[2]}.`;
  }

  match = message.match(/^Efeito '(.+?)' removido de (.+?)\.$/i);
  if (match) {
    return `Effect '${replaceTokenSet(match[1], "en", EFFECT_TOKENS)}' removed from ${match[2]}.`;
  }

  match = message.match(/^Efeito '(.+?)' expirou em (.+?) \((fim|inicio) do turno de (.+?)\)\.$/i);
  if (match) {
    const when = match[3].toLowerCase() === "fim" ? "end" : "start";
    return `Effect '${replaceTokenSet(match[1], "en", EFFECT_TOKENS)}' expired on ${match[2]} (${when} of ${match[4]}'s turn).`;
  }

  match = message.match(/^(.+?) usou a propria reacao\.$/i);
  if (match) {
    return `${match[1]} used their reaction.`;
  }

  match = message.match(/^(.+?) usa a acao Esquivar\.$/i);
  if (match) {
    return `${match[1]} takes the Dodge action.`;
  }

  match = message.match(/^(.+?) ajuda (.+?) no proximo ataque\.$/i);
  if (match) {
    return `${match[1]} helps ${match[2]} with their next attack.`;
  }

  match = message.match(/^(.+?) tenta se esconder \(Furtividade: (\d+)\)\.$/i);
  if (match) {
    return `${match[1]} attempts to hide (Stealth: ${match[2]}).`;
  }

  match = message.match(/^(.+?) usa (.+?)\.$/i);
  if (match) {
    const description = match[2].toLowerCase() === "um objeto" ? "an object" : match[2];
    return `${match[1]} uses ${description}.`;
  }

  match = message.match(/^(.+?) usa a acao Disparada\.$/i);
  if (match) {
    return `${match[1]} takes the Dash action.`;
  }

  match = message.match(/^(.+?) usa a acao Desengajar\.$/i);
  if (match) {
    return `${match[1]} takes the Disengage action.`;
  }

  match = message.match(/^GM aplicou (\d+) de dano\.(.*)$/i);
  if (match) {
    return `GM applied ${match[1]} damage.${normalizeCombatTail(match[2], "en")}`;
  }

  match = message.match(/^GM aplicou (\d+) de cura\.(.*)$/i);
  if (match) {
    return `GM applied ${match[1]} healing.${normalizeCombatTail(match[2], "en")}`;
  }

  match = message.match(/^(.+?) conjurou (.+?) em (.+?): (\d+) total vs AC (\d+) - (acerto|errou)\.(.*)$/i);
  if (match) {
    const hitText = match[6].toLowerCase() === "acerto" ? "hit" : "missed";
    return `${match[1]} cast ${match[2]} on ${match[3]}: ${match[4]} total vs AC ${match[5]} - ${hitText}.${normalizeCombatTail(match[7], "en")}`;
  }

  match = message.match(/^(.+?) lancou (.+?) em (.+?): alvo (passou|falhou) no save de (.+?) contra CD (\d+)\.(.*)$/i);
  if (match) {
    const outcome = match[4].toLowerCase() === "passou" ? "succeeded" : "failed";
    return `${match[1]} cast ${match[2]} on ${match[3]}: target ${outcome} the ${match[5]} save against DC ${match[6]}.${normalizeCombatTail(match[7], "en")}`;
  }

  match = message.match(/^(.+?) conjurou (.+?) em (.+?)\.(.*)$/i);
  if (match) {
    return `${match[1]} cast ${match[2]} on ${match[3]}.${normalizeCombatTail(match[4], "en")}`;
  }

  if (message === "Combate iniciado! Role a iniciativa.") {
    return "Combat started! Roll for initiative.";
  }
  if (message === "Combate encerrado.") {
    return "Combat ended.";
  }
  if (message === "Iniciativa atualizada.") {
    return "Initiative updated.";
  }

  return replaceTokenSet(replaceTokenSet(message, "en", DAMAGE_TOKENS), "en", EFFECT_TOKENS);
};

export const localizeCombatLogMessage = (message: string, locale: Locale) => {
  const trimmed = message.trim();
  if (!trimmed) {
    return trimmed;
  }

  const localized =
    locale === "pt"
      ? localizeKnownEnglishMessage(trimmed, locale)
      : localizeKnownPortugueseMessage(trimmed, locale);

  return normalizeCombatTail(localized, locale);
};
