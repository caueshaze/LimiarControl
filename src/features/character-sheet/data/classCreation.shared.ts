import { toCatalogStarterToken } from "../utils/creationItemCatalog";
import type { ClassEquipmentOption } from "./classCreation.types";

const slugify = (value: string) =>
  value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const catalogInstrument = (label: string, canonicalKey: string): ClassEquipmentOption => ({
  id: canonicalKey.replace(/_/g, "-"),
  label,
  items: [toCatalogStarterToken(canonicalKey)],
});

export const musicalInstrumentOptions: ClassEquipmentOption[] = [
  catalogInstrument("Alaúde", "lute"),
  catalogInstrument("Flauta", "flute"),
  catalogInstrument("Lira", "lyre"),
  catalogInstrument("Tambor", "drum"),
  catalogInstrument("Viola", "viol"),
  catalogInstrument("Flauta de Pã", "pan_flute"),
];

const pack = (label: string, englishKey: string): ClassEquipmentOption => ({
  id: slugify(englishKey),
  label,
  items: [englishKey],
});

export const packOptions = (...pairs: [string, string][]) =>
  pairs.map(([label, key]) => pack(label, key));
