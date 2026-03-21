export type DragonbornAncestryId =
  | "black"
  | "blue"
  | "brass"
  | "bronze"
  | "copper"
  | "gold"
  | "green"
  | "red"
  | "silver"
  | "white";

export type DragonbornAncestry = {
  id: DragonbornAncestryId;
  label: string;
  damageType: string;
  resistanceType: string;
  area: {
    shape: "line" | "cone";
    size: string;
  };
  saveAbility: "DEX" | "CON";
};

export const DRAGONBORN_ANCESTRIES: DragonbornAncestry[] = [
  { id: "black", label: "Black", damageType: "acid", resistanceType: "acid", area: { shape: "line", size: "1.5m x 9m" }, saveAbility: "DEX" },
  { id: "blue", label: "Blue", damageType: "lightning", resistanceType: "lightning", area: { shape: "line", size: "1.5m x 9m" }, saveAbility: "DEX" },
  { id: "brass", label: "Brass", damageType: "fire", resistanceType: "fire", area: { shape: "line", size: "1.5m x 9m" }, saveAbility: "DEX" },
  { id: "bronze", label: "Bronze", damageType: "lightning", resistanceType: "lightning", area: { shape: "line", size: "1.5m x 9m" }, saveAbility: "DEX" },
  { id: "copper", label: "Copper", damageType: "acid", resistanceType: "acid", area: { shape: "line", size: "1.5m x 9m" }, saveAbility: "DEX" },
  { id: "gold", label: "Gold", damageType: "fire", resistanceType: "fire", area: { shape: "cone", size: "4.5m" }, saveAbility: "DEX" },
  { id: "green", label: "Green", damageType: "poison", resistanceType: "poison", area: { shape: "cone", size: "4.5m" }, saveAbility: "CON" },
  { id: "red", label: "Red", damageType: "fire", resistanceType: "fire", area: { shape: "cone", size: "4.5m" }, saveAbility: "DEX" },
  { id: "silver", label: "Silver", damageType: "cold", resistanceType: "cold", area: { shape: "cone", size: "4.5m" }, saveAbility: "CON" },
  { id: "white", label: "White", damageType: "cold", resistanceType: "cold", area: { shape: "cone", size: "4.5m" }, saveAbility: "CON" },
];

export const getDragonbornAncestry = (id: string | null | undefined): DragonbornAncestry | undefined =>
  DRAGONBORN_ANCESTRIES.find((ancestry) => ancestry.id === id);

export const isDragonbornAncestryId = (id: string | null | undefined): id is DragonbornAncestryId =>
  !!id && DRAGONBORN_ANCESTRIES.some((ancestry) => ancestry.id === id);
