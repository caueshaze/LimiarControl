import armorCsv from "../../../Base/DND5e_Armaduras_Database.csv?raw";
import gearCsv from "../../../Base/DND5e_Equipamentos_Database.csv?raw";
import weaponCsv from "../../../Base/DND5e_Armas_Database_Programador.csv?raw";
import { parseCsvObjects } from "../../shared/lib/csv";

export type CoinType = "cp" | "sp" | "ep" | "gp" | "pp";
export type BaseWeaponCategory = "simple" | "martial";
export type BaseWeaponKind = "melee" | "ranged";
export type BaseArmorCategory = "light" | "medium" | "heavy" | "shield";

type WeaponRow = {
  canonical_key: string;
  Nome: string;
  Categoria: string;
  Tipo: string;
  Custo: string;
  Dano: string;
  "Tipo de dano": string;
  Peso: string;
  Propriedades: string;
  "Alcance normal": string;
  "Alcance máximo": string;
  "Dano versátil": string;
  "Descrição curta": string;
};

type ArmorRow = {
  canonical_key: string;
  Nome: string;
  Categoria: string;
  Custo: string;
  "CA base": string;
  "Mod DEX máximo": string;
  "Requisito de FOR": string;
  "Desvantagem em furtividade": string;
  Peso: string;
  Descrição: string;
};

type GearRow = {
  canonical_key: string;
  Nome: string;
  Tipo: string;
  Categoria: string;
  Custo: string;
  Peso: string;
  "Descrição": string;
};

export type BasePrice = {
  amount: number;
  coin: CoinType;
  gpValue: number;
  label: string;
};

export type BaseWeapon = {
  canonicalKey: string;
  name: string;
  category: BaseWeaponCategory;
  kind: BaseWeaponKind;
  price: BasePrice;
  damageDice: string | null;
  damageType: string | null;
  weightLb: number | null;
  properties: string[];
  normalRangeFt: number | null;
  maxRangeFt: number | null;
  versatileDamage: string | null;
  description: string;
};

export type BaseArmor = {
  canonicalKey: string;
  name: string;
  category: BaseArmorCategory;
  price: BasePrice;
  baseAC: number;
  dexCap: number | null;
  strengthRequirement: number | null;
  stealthDisadvantage: boolean;
  weightLb: number | null;
  description: string;
};

export type BaseGear = {
  canonicalKey: string;
  name: string;
  itemKind: string;
  equipmentCategory: string;
  price: BasePrice | null;
  weightLb: number | null;
  description: string;
};

const GP_VALUES: Record<CoinType, number> = {
  cp: 0.01,
  sp: 0.1,
  ep: 0.5,
  gp: 1,
  pp: 10,
};

const parsePrice = (raw: string): BasePrice => {
  const match = raw.trim().match(/^([\d.]+)\s*(cp|sp|ep|gp|pp)$/i);
  if (!match) {
    return { amount: 0, coin: "gp", gpValue: 0, label: raw.trim() || "0 gp" };
  }
  const amount = Number(match[1]);
  const coin = match[2].toLowerCase() as CoinType;
  return {
    amount,
    coin,
    gpValue: amount * GP_VALUES[coin],
    label: `${amount} ${coin}`,
  };
};

const parseWeight = (raw: string) => {
  const match = raw.trim().match(/[\d.]+/);
  return match ? Number(match[0]) : null;
};

const parseIntCell = (raw: string) => {
  const value = Number(raw.trim());
  return Number.isFinite(value) ? value : null;
};

const parseDexCap = (raw: string) => {
  if (raw.trim().toLowerCase() === "ilimitado") return null;
  if (raw.trim().toUpperCase() === "N/A") return 0;
  return parseIntCell(raw);
};

const mapWeaponCategory = (raw: string): BaseWeaponCategory =>
  raw.trim().toLowerCase() === "marcial" ? "martial" : "simple";

const mapWeaponKind = (raw: string): BaseWeaponKind =>
  raw.trim().toLowerCase().includes("dist") ? "ranged" : "melee";

const mapArmorCategory = (raw: string): BaseArmorCategory => {
  const value = raw.trim().toLowerCase();
  if (value === "leve") return "light";
  if (value === "média" || value === "media") return "medium";
  if (value === "pesada") return "heavy";
  return "shield";
};

const parseProperties = (raw: string) =>
  raw
    .split(",")
    .map((entry) => entry.trim())
    .filter((entry) => entry && entry !== "-");

export const BASE_WEAPONS: BaseWeapon[] = parseCsvObjects<keyof WeaponRow>(weaponCsv).map((row) => ({
  canonicalKey: row.canonical_key,
  name: row.Nome,
  category: mapWeaponCategory(row.Categoria),
  kind: mapWeaponKind(row.Tipo),
  price: parsePrice(row.Custo),
  damageDice: row.Dano && row.Dano !== "-" ? row.Dano : null,
  damageType: row["Tipo de dano"] && row["Tipo de dano"] !== "-" ? row["Tipo de dano"] : null,
  weightLb: parseWeight(row.Peso),
  properties: parseProperties(row.Propriedades),
  normalRangeFt: parseIntCell(row["Alcance normal"]),
  maxRangeFt: parseIntCell(row["Alcance máximo"]),
  versatileDamage: row["Dano versátil"] || null,
  description: row["Descrição curta"],
}));

export const BASE_ARMORS: BaseArmor[] = parseCsvObjects<keyof ArmorRow>(armorCsv).map((row) => ({
  canonicalKey: row.canonical_key,
  name: row.Nome,
  category: mapArmorCategory(row.Categoria),
  price: parsePrice(row.Custo),
  baseAC: Number(row["CA base"]) || 0,
  dexCap: parseDexCap(row["Mod DEX máximo"]),
  strengthRequirement: parseIntCell(row["Requisito de FOR"]),
  stealthDisadvantage: row["Desvantagem em furtividade"].trim().toLowerCase() === "sim",
  weightLb: parseWeight(row.Peso),
  description: row.Descrição,
}));

export const BASE_GEARS: BaseGear[] = parseCsvObjects<keyof GearRow>(gearCsv).map((row) => ({
  canonicalKey: row.canonical_key,
  name: row.Nome,
  itemKind: row.Tipo,
  equipmentCategory: row.Categoria,
  price: row.Custo ? parsePrice(row.Custo) : null,
  weightLb: row.Peso ? parseWeight(row.Peso) : null,
  description: row["Descrição"],
}));

export const findBaseWeapon = (name: string) =>
  BASE_WEAPONS.find((weapon) => weapon.name.toLowerCase() === name.trim().toLowerCase());

export const findBaseArmor = (name: string) =>
  BASE_ARMORS.find((armor) => armor.name.toLowerCase() === name.trim().toLowerCase());

export const findBaseGear = (name: string) =>
  BASE_GEARS.find((gear) => gear.name.toLowerCase() === name.trim().toLowerCase());

export const getBaseWeapons = (filter?: Partial<Pick<BaseWeapon, "category" | "kind">>) =>
  BASE_WEAPONS.filter((weapon) => {
    if (filter?.category && weapon.category !== filter.category) return false;
    if (filter?.kind && weapon.kind !== filter.kind) return false;
    return true;
  });

export const getBaseArmors = (filter?: Partial<Pick<BaseArmor, "category">>) =>
  BASE_ARMORS.filter((armor) => {
    if (filter?.category && armor.category !== filter.category) return false;
    return true;
  });
