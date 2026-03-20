export type CreationWeaponCategory = "simple" | "martial";
export type CreationWeaponKind = "melee" | "ranged";

export type CreationWeapon = {
  name: string;
  label: string;
  category: CreationWeaponCategory;
  kind: CreationWeaponKind;
};

const CREATION_WEAPONS: CreationWeapon[] = [
  { name: "Dagger", label: "Adaga", category: "simple", kind: "melee" },
  { name: "Quarterstaff", label: "Cajado", category: "simple", kind: "melee" },
  { name: "Club", label: "Clava", category: "simple", kind: "melee" },
  { name: "Greatclub", label: "Clava Grande", category: "simple", kind: "melee" },
  { name: "Sickle", label: "Foice", category: "simple", kind: "melee" },
  { name: "Spear", label: "Lança", category: "simple", kind: "melee" },
  { name: "Javelin", label: "Lança Curta", category: "simple", kind: "melee" },
  { name: "Mace", label: "Maça", category: "simple", kind: "melee" },
  { name: "Handaxe", label: "Machado de Mão", category: "simple", kind: "melee" },
  { name: "Light Hammer", label: "Martelo Leve", category: "simple", kind: "melee" },
  { name: "Shortbow", label: "Arco Curto", category: "simple", kind: "ranged" },
  { name: "Sling", label: "Atiradeira (Funda)", category: "simple", kind: "ranged" },
  { name: "Light Crossbow", label: "Besta Leve", category: "simple", kind: "ranged" },
  { name: "Dart", label: "Dardo", category: "simple", kind: "ranged" },
  { name: "Halberd", label: "Alabarda", category: "martial", kind: "melee" },
  { name: "Whip", label: "Chicote", category: "martial", kind: "melee" },
  { name: "Scimitar", label: "Cimitarra", category: "martial", kind: "melee" },
  { name: "Shortsword", label: "Espada Curta", category: "martial", kind: "melee" },
  { name: "Greatsword", label: "Espada Grande", category: "martial", kind: "melee" },
  { name: "Longsword", label: "Espada Longa", category: "martial", kind: "melee" },
  { name: "Glaive", label: "Glaive", category: "martial", kind: "melee" },
  { name: "Lance", label: "Lança de Montaria", category: "martial", kind: "melee" },
  { name: "Battleaxe", label: "Machado de Batalha", category: "martial", kind: "melee" },
  { name: "Greataxe", label: "Machado Grande", category: "martial", kind: "melee" },
  { name: "Maul", label: "Malho", category: "martial", kind: "melee" },
  { name: "Flail", label: "Mangual", category: "martial", kind: "melee" },
  { name: "Morningstar", label: "Manhã-Estrela", category: "martial", kind: "melee" },
  { name: "Warhammer", label: "Martelo de Guerra", category: "martial", kind: "melee" },
  { name: "War Pick", label: "Picareta de Guerra", category: "martial", kind: "melee" },
  { name: "Pike", label: "Pique", category: "martial", kind: "melee" },
  { name: "Rapier", label: "Rapieira", category: "martial", kind: "melee" },
  { name: "Trident", label: "Tridente", category: "martial", kind: "melee" },
  { name: "Longbow", label: "Arco Longo", category: "martial", kind: "ranged" },
  { name: "Hand Crossbow", label: "Besta de Mão", category: "martial", kind: "ranged" },
  { name: "Heavy Crossbow", label: "Besta Pesada", category: "martial", kind: "ranged" },
  { name: "Net", label: "Rede", category: "martial", kind: "ranged" },
];

export const getCreationWeapons = (
  filter?: Partial<Pick<CreationWeapon, "category" | "kind">>,
) =>
  CREATION_WEAPONS.filter((weapon) => {
    if (filter?.category && weapon.category !== filter.category) {
      return false;
    }
    if (filter?.kind && weapon.kind !== filter.kind) {
      return false;
    }
    return true;
  });
