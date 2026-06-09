import type { AbilityName, CharacterSheet } from "../../model/characterSheet.types";
import { ABILITIES, ABILITY_SHORT, SKILL_ABILITY_MAP, SKILL_LABELS, SKILL_NAMES } from "../../constants";
import {
  computeSaveMod,
  computeSkillMod,
  computeWeaponAttack,
  computeWeaponDamage,
  formatMod,
} from "../../utils/calculations";
import { useCharacterSheetDerived } from "../../hooks/useCharacterSheetDerived";
import { getClass, getSubclassDisplayName } from "../../data/classes";
import { getRace } from "../../data/races";
import { getBackground } from "../../data/backgrounds";
import { getXpForNextLevel } from "../../data/xpThresholds";
import { getCatalogSpellOptions } from "../../utils/creationSpells";
import { resolveSpellByAuthority } from "../../../../entities/dnd-base";
import { parseCreationPersonalityFields } from "../../utils/creationPersonality";
import { fromCopper } from "../../../../shared/utils/money";
import { ManagedImage } from "../../../../shared/ui/ManagedImage";
import { BackButton } from "../../../../shared/ui/BackButton";
import { useLocale } from "../../../../shared/hooks/useLocale";
import { localizeDamageType } from "../../../../shared/i18n/domain/damage";
import { localizeSpellSchool } from "../../../../shared/i18n/domain/spell";

type Props = {
  sheet: CharacterSheet;
  campaignId?: string | null;
  backHref?: string | null;
  backLabel?: string | null;
};

const SPELL_SCHOOL_KEYS = new Set([
  "abjuration",
  "conjuration",
  "divination",
  "enchantment",
  "evocation",
  "illusion",
  "necromancy",
  "transmutation",
]);

const formatNumber = (value: number) => value.toLocaleString("pt-BR");

const formatMeters = (value: number) =>
  Number.isInteger(value) ? `${value} m` : `${value.toFixed(1).replace(".", ",")} m`;

const initialsOf = (name: string) =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";

// ── Shared presentational pieces ─────────────────────────────────────────────

const Panel = ({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) => (
  <section
    className={`rounded-2xl border border-amber-500/20 bg-[linear-gradient(180deg,rgba(20,15,8,0.55),rgba(8,6,12,0.85))] p-4 shadow-[inset_0_1px_0_rgba(251,191,36,0.06)] ${className}`}
  >
    {title ? (
      <h3 className="mb-3 font-display text-[11px] font-bold uppercase tracking-[0.26em] text-amber-300/90">
        {title}
      </h3>
    ) : null}
    {children}
  </section>
);

const LabeledValue = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <div className="flex items-baseline justify-between gap-3 border-b border-white/5 py-1.5 last:border-b-0">
    <span className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</span>
    <span className="text-right text-sm font-medium text-slate-100">{value || "—"}</span>
  </div>
);

const Dot = ({ filled }: { filled: boolean }) => (
  <span
    className={`inline-block h-3 w-3 shrink-0 rounded-full border ${
      filled ? "border-amber-400 bg-amber-400/80" : "border-slate-600 bg-transparent"
    }`}
  />
);

// ── Main view ────────────────────────────────────────────────────────────────

export const CharacterSheetView = ({ sheet, campaignId = null, backHref = null, backLabel = null }: Props) => {
  const { locale } = useLocale();
  const derived = useCharacterSheetDerived(sheet, null);
  const classData = getClass(sheet.class);
  const raceData = getRace(sheet.race, sheet.raceConfig);
  const backgroundData = getBackground(sheet.background);
  const subclassName = getSubclassDisplayName(sheet.class, sheet.subclass, sheet.subclassConfig);
  const personality = parseCreationPersonalityFields(sheet.featuresAndTraits);
  const wallet = fromCopper(sheet.currency.copperValue);
  const nextLevelXp = getXpForNextLevel(sheet.level);

  const raceClassLine = [raceData?.name ?? sheet.race, classData?.name ?? sheet.class]
    .filter(Boolean)
    .join(" • ");

  const spellcasting = sheet.spellcasting;
  const spellAbilityLabel = spellcasting
    ? ABILITIES.find((ability) => ability.key === spellcasting.ability)?.label ?? ""
    : "";
  const spellLevels = spellcasting
    ? Array.from({ length: 10 }, (_, level) => ({
        level,
        spells: spellcasting.spells.filter((spell) => spell.level === level),
      })).filter((group) => group.spells.length > 0)
    : [];
  const spellSlots = spellcasting
    ? Object.entries(spellcasting.slots)
        .map(([level, slot]) => ({ level: Number(level), max: slot.max, used: slot.used }))
        .filter((slot) => slot.max > 0)
        .sort((a, b) => a.level - b.level)
    : [];
  const schoolLabel = (school: string): string => {
    const key = school.trim().toLowerCase();
    return SPELL_SCHOOL_KEYS.has(key)
      ? localizeSpellSchool(key as Parameters<typeof localizeSpellSchool>[0], locale)
      : school;
  };
  const spellLevelLabel = (level: number) => (level === 0 ? "Truques" : `${level}º Nível`);
  // Stored spells only carry the English name; resolve the localized name from
  // the catalog (loaded by useCharacterSheetView) via authority precedence.
  const spellCatalog = spellcasting ? getCatalogSpellOptions(sheet.class, campaignId) : [];
  const spellDisplayName = (spell: { name: string; canonicalKey?: string | null; campaignSpellId?: string | null }) => {
    const match = resolveSpellByAuthority(spellCatalog, spell);
    if (match) {
      return locale === "pt" ? match.namePt ?? match.name : match.name;
    }
    return spell.name;
  };

  const coins: { label: string; value: number }[] = [
    { label: "PP", value: wallet.pp },
    { label: "PO", value: wallet.gp },
    { label: "PE", value: wallet.ep },
    { label: "PR", value: wallet.sp },
    { label: "PC", value: wallet.cp },
  ];

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[radial-gradient(circle_at_top,rgba(251,191,36,0.06),transparent_26%),linear-gradient(180deg,#05040a_0%,#05040a_55%,#080611_100%)] text-slate-100">
      <div className="relative mx-auto max-w-300 px-4 py-6 lg:px-6">
        {backHref || backLabel ? (
          <div className="mb-4">
            <BackButton
              label={`← ${backLabel ?? "Voltar"}`}
              fallbackTo={backHref}
              className="rounded-full border border-amber-500/25 bg-white/3 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-amber-200/90 transition hover:border-amber-400/50 hover:text-amber-100"
            />
          </div>
        ) : null}

        {/* Ornate sheet frame */}
        <div className="rounded-[28px] border border-amber-500/30 bg-[linear-gradient(180deg,rgba(10,8,16,0.92),rgba(5,4,10,0.97))] p-5 shadow-[0_30px_90px_rgba(0,0,0,0.55)] lg:p-7">
          {/* Header */}
          <header className="grid gap-5 border-b border-amber-500/20 pb-6 lg:grid-cols-[auto_1fr_auto] lg:items-center">
            <div className="flex items-center gap-4 lg:order-2 lg:justify-self-start">
              <Portrait avatarUrl={sheet.avatarUrl} name={sheet.name} />
              <div>
                <h1 className="font-display text-2xl font-bold tracking-wide text-slate-50 sm:text-3xl">
                  {sheet.name || "Sem nome"}
                </h1>
                <p className="mt-1 text-sm text-slate-400">{raceClassLine}</p>
                <p className="mt-1 text-xs font-bold uppercase tracking-[0.24em] text-amber-300/90">
                  Nível {sheet.level}
                </p>
              </div>
            </div>

            <div className="text-center lg:order-1 lg:row-span-1 lg:justify-self-start lg:text-left">
              <p className="font-display text-3xl font-extrabold tracking-[0.18em] text-amber-300 sm:text-4xl">
                LIMIAR
              </p>
              <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.42em] text-slate-500">
                Ficha de Personagem
              </p>
            </div>

            <div className="lg:order-3 lg:w-64 lg:justify-self-end">
              <Panel className="!p-3">
                <LabeledValue label="Jogador" value={sheet.playerName} />
                <LabeledValue
                  label="Experiência"
                  value={
                    nextLevelXp != null
                      ? `${formatNumber(sheet.experiencePoints)} / ${formatNumber(nextLevelXp)}`
                      : formatNumber(sheet.experiencePoints)
                  }
                />
                <LabeledValue label="Alinhamento" value={sheet.alignment} />
                <LabeledValue
                  label="Inspiração"
                  value={<Dot filled={sheet.inspiration} />}
                />
              </Panel>
            </div>
          </header>

          {/* Ability scores */}
          <div className="mt-6 grid grid-cols-3 gap-3 sm:grid-cols-6">
            {ABILITIES.map((ability) => (
              <AbilityBox key={ability.key} abilityKey={ability.key} short={ability.short} score={sheet.abilities[ability.key]} />
            ))}
          </div>

          {/* Core combat / identity / saves / perception */}
          <div className="mt-4 grid gap-3 lg:grid-cols-12">
            {/* Identity + defenses */}
            <div className="space-y-3 lg:col-span-4">
              <Panel>
                <LabeledValue label="Classe" value={classData?.name ?? sheet.class} />
                {subclassName ? <LabeledValue label="Arquétipo" value={subclassName} /> : null}
                <LabeledValue label="Antecedente" value={backgroundData?.name ?? sheet.background} />
                <LabeledValue label="Idiomas" value={sheet.languages.join(", ")} />
                <LabeledValue label="Tendência" value={sheet.alignment || "Nenhuma"} />
              </Panel>
              <div className="grid grid-cols-3 gap-3">
                <BigStat label="Classe de Armadura" value={String(derived.ac)} />
                <BigStat label="Iniciativa" value={formatMod(derived.initiative)} />
                <BigStat label="Deslocamento" value={formatMeters(derived.effectiveSpeedMeters)} />
              </div>
            </div>

            {/* Vitals */}
            <div className="lg:col-span-4">
              <Panel title="Pontos de Vida" className="h-full">
                <div className="text-center">
                  <p className="font-display text-4xl font-extrabold text-emerald-300">
                    {sheet.currentHP}
                    <span className="text-slate-500"> / {sheet.maxHP}</span>
                  </p>
                  <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                    PV Atuais / Máximos
                  </p>
                  {sheet.tempHP > 0 ? (
                    <p className="mt-1 text-xs font-semibold text-sky-300">+{sheet.tempHP} PV temporários</p>
                  ) : null}
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <BigStat
                    label="Dado de Vida"
                    value={`${sheet.hitDiceRemaining}/${sheet.hitDiceTotal}${sheet.hitDiceType ? ` ${sheet.hitDiceType}` : ""}`}
                  />
                  <BigStat label="Bônus de Proficiência" value={formatMod(derived.profBonus)} />
                </div>
              </Panel>
            </div>

            {/* Saving throws + perception */}
            <div className="space-y-3 lg:col-span-4">
              <Panel title="Testes de Resistência">
                <div className="space-y-1">
                  {ABILITIES.map((ability) => {
                    const proficient = sheet.savingThrowProficiencies[ability.key];
                    const value = computeSaveMod(
                      ability.key,
                      sheet.abilities[ability.key],
                      proficient,
                      sheet.level,
                    );
                    return (
                      <div key={ability.key} className="flex items-center gap-2.5 py-0.5">
                        <Dot filled={proficient} />
                        <span className="flex-1 text-sm text-slate-300">{ability.label}</span>
                        <span className="rounded-full bg-slate-950/70 px-2.5 py-0.5 text-sm font-bold text-slate-100">
                          {formatMod(value)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Panel>
              <Panel title="Percepção Passiva">
                <p className="text-center font-display text-3xl font-extrabold text-cyan-300">
                  {derived.passivePerception}
                </p>
                {raceData?.darkvisionMeters ? (
                  <p className="mt-3 text-center text-xs text-slate-400">
                    <span className="font-semibold uppercase tracking-[0.18em] text-slate-500">Sentidos:</span>{" "}
                    Visão no Escuro {formatMeters(raceData.darkvisionMeters)}
                  </p>
                ) : null}
              </Panel>
            </div>
          </div>

          {/* Attacks + skills + equipment */}
          <div className="mt-4 grid gap-3 lg:grid-cols-12">
            <div className="space-y-3 lg:col-span-5">
              <Panel title="Ataques e Conjurações">
                {sheet.weapons.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhum ataque registrado.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                        <th className="pb-2 text-left font-semibold">Nome</th>
                        <th className="pb-2 text-center font-semibold">Bônus</th>
                        <th className="pb-2 text-right font-semibold">Dano / Efeito</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sheet.weapons.map((weapon) => (
                        <tr key={weapon.id} className="border-t border-white/5">
                          <td className="py-1.5 pr-2 text-slate-200">{weapon.name}</td>
                          <td className="py-1.5 text-center font-bold text-amber-200">
                            {formatMod(computeWeaponAttack(weapon, sheet.abilities, sheet.level, sheet.fightingStyle))}
                          </td>
                          <td className="py-1.5 text-right text-slate-300">
                            {computeWeaponDamage(weapon, sheet.abilities)}
                            {weapon.damageType ? ` ${localizeDamageType(weapon.damageType, locale) ?? weapon.damageType}` : ""}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </Panel>

              <Panel title="Equipamento">
                {sheet.inventory.length === 0 ? (
                  <p className="text-sm text-slate-500">Nenhum item.</p>
                ) : (
                  <ul className="space-y-1 text-sm text-slate-300">
                    {sheet.inventory.map((item) => (
                      <li key={item.id} className="flex items-baseline gap-2">
                        <span className="text-amber-400/70">•</span>
                        <span className="flex-1">{item.name}</span>
                        {item.quantity > 1 ? (
                          <span className="text-xs text-slate-500">×{item.quantity}</span>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>

            <div className="lg:col-span-7">
              <Panel title="Habilidades" className="h-full">
                <div className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                  {SKILL_NAMES.map((skill) => {
                    const total = computeSkillMod(skill, sheet.abilities, sheet.skillProficiencies, sheet.level);
                    return (
                      <div key={skill} className="flex items-center gap-2.5 py-0.5">
                        <Dot filled={sheet.skillProficiencies[skill] > 0} />
                        <span className="flex-1 truncate text-sm text-slate-300">
                          {SKILL_LABELS[skill]}{" "}
                          <span className="text-[10px] uppercase tracking-wider text-slate-500">
                            ({ABILITY_SHORT[SKILL_ABILITY_MAP[skill]]})
                          </span>
                        </span>
                        <span className="rounded-full bg-slate-950/70 px-2.5 py-0.5 text-sm font-bold text-slate-100">
                          {formatMod(total)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </Panel>
            </div>
          </div>

          {/* Spellcasting */}
          {spellcasting ? (
            <div className="mt-4">
              <Panel title="Conjurações">
                <div className="grid grid-cols-3 gap-3">
                  <BigStat label="Atributo de Conjuração" value={spellAbilityLabel || "—"} />
                  <BigStat label="CD de Resistência" value={derived.spellSaveDC != null ? String(derived.spellSaveDC) : "—"} />
                  <BigStat label="Bônus de Ataque" value={derived.spellAttack != null ? formatMod(derived.spellAttack) : "—"} />
                </div>

                {spellSlots.length > 0 ? (
                  <div className="mt-4">
                    <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                      Espaços de Magia
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {spellSlots.map((slot) => (
                        <div
                          key={slot.level}
                          className="flex min-w-16 flex-col items-center rounded-xl border border-amber-500/15 bg-slate-950/50 px-3 py-2"
                        >
                          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                            Nível {slot.level}
                          </span>
                          <span className="text-sm font-bold text-slate-100">
                            {Math.max(0, slot.max - slot.used)}
                            <span className="text-slate-500"> / {slot.max}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="mt-4 space-y-4">
                  {spellLevels.length === 0 ? (
                    <p className="text-sm text-slate-500">Nenhuma magia registrada.</p>
                  ) : (
                    spellLevels.map((group) => (
                      <div key={group.level}>
                        <p className="mb-1.5 border-b border-white/6 pb-1 text-[11px] font-bold uppercase tracking-[0.2em] text-amber-300/90">
                          {spellLevelLabel(group.level)}
                        </p>
                        <ul className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                          {group.spells.map((spell) => (
                            <li key={spell.id} className="flex items-baseline gap-2 py-0.5">
                              <Dot filled={spell.prepared} />
                              <span className="flex-1 text-sm text-slate-200">{spellDisplayName(spell)}</span>
                              {spell.school ? (
                                <span className="text-[10px] uppercase tracking-wider text-slate-500">
                                  {schoolLabel(spell.school)}
                                </span>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))
                  )}
                </div>
              </Panel>
            </div>
          ) : null}

          {/* Features / origin */}
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            <Panel title="Traços e Recursos">
              {sheet.classFeatures.length === 0 ? (
                <p className="text-sm text-slate-500">Nenhum traço registrado.</p>
              ) : (
                <ul className="space-y-3">
                  {sheet.classFeatures.map((feature) => (
                    <li key={feature.id}>
                      <p className="text-sm font-semibold text-amber-200/90">{feature.label}</p>
                      {feature.description ? (
                        <p className="mt-0.5 text-xs leading-5 text-slate-400">{feature.description}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Origem do Personagem">
              <div className="space-y-3 text-sm text-slate-300">
                <OriginField label="Traços de Personalidade" value={personality.personalityTraits} />
                <OriginField label="Ideal" value={personality.ideals} />
                <OriginField label="Vínculo" value={personality.bonds} />
                <OriginField label="Defeito" value={personality.flaws} />
              </div>
            </Panel>
          </div>

          {/* Currency */}
          <div className="mt-4">
            <Panel title="Moedas e Itens">
              <div className="grid grid-cols-5 gap-3">
                {coins.map((coin) => (
                  <div
                    key={coin.label}
                    className="flex flex-col items-center gap-1 rounded-xl border border-amber-500/15 bg-slate-950/50 py-2"
                  >
                    <span className="text-[10px] font-bold uppercase tracking-widest text-amber-300/80">
                      {coin.label}
                    </span>
                    <span className="text-lg font-bold text-slate-100">{coin.value}</span>
                  </div>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Subcomponents ────────────────────────────────────────────────────────────

const Portrait = ({ avatarUrl, name }: { avatarUrl: string | null; name: string }) => (
  <div className="relative h-20 w-20 shrink-0 overflow-hidden rounded-full border-2 border-amber-500/50 bg-[radial-gradient(circle_at_30%_20%,rgba(251,191,36,0.18),rgba(8,6,12,0.95))] shadow-[0_0_24px_rgba(251,191,36,0.15)] sm:h-24 sm:w-24">
    {avatarUrl ? (
      <ManagedImage src={avatarUrl} alt={name} className="h-full w-full object-cover" />
    ) : null}
    {!avatarUrl ? (
      <span className="flex h-full w-full items-center justify-center font-display text-2xl font-bold text-amber-200/80">
        {initialsOf(name)}
      </span>
    ) : null}
  </div>
);

const AbilityBox = ({
  abilityKey,
  short,
  score,
}: {
  abilityKey: AbilityName;
  short: string;
  score: number;
}) => {
  const mod = Math.floor((score - 10) / 2);
  return (
    <div
      key={abilityKey}
      className="flex flex-col items-center rounded-2xl border border-amber-500/20 bg-[linear-gradient(180deg,rgba(20,15,8,0.6),rgba(8,6,12,0.9))] py-3"
    >
      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-amber-300/80">{short}</span>
      <span className="font-display text-2xl font-extrabold text-slate-50">{score}</span>
      <span className="text-xs font-semibold text-slate-400">{formatMod(mod)}</span>
    </div>
  );
};

const BigStat = ({ label, value }: { label: string; value: string }) => (
  <div className="flex flex-col items-center justify-center rounded-2xl border border-amber-500/20 bg-slate-950/50 px-2 py-3 text-center">
    <span className="font-display text-xl font-extrabold text-slate-50">{value}</span>
    <span className="mt-1 text-[9px] font-semibold uppercase leading-tight tracking-[0.16em] text-slate-500">
      {label}
    </span>
  </div>
);

const OriginField = ({ label, value }: { label: string; value: string }) =>
  value.trim() ? (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-amber-300/70">{label}</p>
      <p className="mt-0.5 text-sm leading-6 text-slate-300">{value}</p>
    </div>
  ) : null;
