import spellsCsv from "../../../Base/DND5e_Magias_Completas_API.csv?raw";
import { parseCsvObjects } from "../../shared/lib/csv";

type SpellRow = {
  Nome: string;
  Nível: string;
  Escola: string;
  "Tempo de conjuração": string;
  Alcance: string;
  Componentes: string;
  Duração: string;
  Concentração: string;
  Ritual: string;
  Descrição: string;
  "Tipo de dano": string;
  "Teste de resistência": string;
  "Classe(s)": string;
};

export type BaseSpell = {
  name: string;
  level: number;
  school: string;
  castingTime: string;
  range: string;
  components: string;
  duration: string;
  concentration: boolean;
  ritual: boolean;
  description: string;
  damageType: string | null;
  savingThrow: string | null;
  classes: string[];
};

export const BASE_SPELLS: BaseSpell[] = parseCsvObjects<keyof SpellRow>(spellsCsv).map((row) => ({
  name: row.Nome,
  level: Number(row.Nível) || 0,
  school: row.Escola,
  castingTime: row["Tempo de conjuração"],
  range: row.Alcance,
  components: row.Componentes,
  duration: row.Duração,
  concentration: row.Concentração.trim().toLowerCase() === "sim",
  ritual: row.Ritual.trim().toLowerCase() === "sim",
  description: row.Descrição,
  damageType: row["Tipo de dano"] && row["Tipo de dano"] !== "-" ? row["Tipo de dano"] : null,
  savingThrow: row["Teste de resistência"] && row["Teste de resistência"] !== "-" ? row["Teste de resistência"] : null,
  classes: row["Classe(s)"]
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean),
}));

export const getBaseSpellsForClass = (className: string, maxLevel = 9) =>
  BASE_SPELLS.filter(
    (spell) => spell.level <= maxLevel && spell.classes.some((entry) => entry.toLowerCase() === className.trim().toLowerCase()),
  );

export const findBaseSpell = (name: string) =>
  BASE_SPELLS.find((spell) => spell.name.toLowerCase() === name.trim().toLowerCase());
