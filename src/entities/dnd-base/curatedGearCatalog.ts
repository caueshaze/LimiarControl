export type CuratedGearSeed = {
  name: string;
  price: string | null;
  weightLb: number | null;
  description: string;
};

// Temporary curated subset while the frontend stops depending on the deleted
// runtime JSON catalog. This keeps character creation and the current D&D seed
// path working until the persisted base catalog fully replaces it.
export const CURATED_DND_BASE_GEARS: CuratedGearSeed[] = [
  {
    name: "Arcane Focus",
    price: "10 gp",
    weightLb: null,
    description: "Spellcasting focus used by arcane casters.",
  },
  {
    name: "Druidic Focus",
    price: "1 gp",
    weightLb: null,
    description: "Spellcasting focus used by druids.",
  },
  {
    name: "Holy Symbol",
    price: "5 gp",
    weightLb: 1,
    description: "Divine focus used by clerics and paladins.",
  },
  {
    name: "Crossbow bolt",
    price: "0.05 gp",
    weightLb: 0.075,
    description: "Ammunition for hand, light, and heavy crossbows.",
  },
  {
    name: "Arrow",
    price: "0.05 gp",
    weightLb: 0.05,
    description: "Standard ammunition for bows.",
  },
  {
    name: "Quiver",
    price: "1 gp",
    weightLb: 1,
    description: "Case used to carry arrows or bolts.",
  },
  {
    name: "Thieves' Tools",
    price: "25 gp",
    weightLb: 1,
    description: "Lockpicks and precision tools used by rogues.",
  },
  {
    name: "Forgery Kit",
    price: "15 gp",
    weightLb: 5,
    description: "Tools and materials used to create false documents.",
  },
  {
    name: "Component Pouch",
    price: "25 gp",
    weightLb: 2,
    description: "Small pouch filled with spellcasting material components.",
  },
  {
    name: "Spellbook",
    price: "50 gp",
    weightLb: 3,
    description: "Wizard spellbook used to record arcane formulas.",
  },
  {
    name: "Explorer's Pack",
    price: "10 gp",
    weightLb: 59,
    description: "General-purpose pack for outdoor travel and dungeon delving.",
  },
  {
    name: "Dungeoneer's Pack",
    price: "12 gp",
    weightLb: 61.5,
    description: "Utility pack suited for exploration in enclosed spaces.",
  },
  {
    name: "Priest's Pack",
    price: "19 gp",
    weightLb: 24,
    description: "Pack carrying basic devotional and travel supplies.",
  },
  {
    name: "Scholar's Pack",
    price: "40 gp",
    weightLb: 10,
    description: "Study pack with writing, reference, and research essentials.",
  },
  {
    name: "Burglar's Pack",
    price: "16 gp",
    weightLb: 46.5,
    description: "Pack with stealth and infiltration essentials.",
  },
  {
    name: "Diplomat's Pack",
    price: "39 gp",
    weightLb: 39,
    description: "Formal pack with supplies suited for noble travel.",
  },
  {
    name: "Entertainer's Pack",
    price: "40 gp",
    weightLb: 38,
    description: "Pack with practical supplies for performers on the road.",
  },
  {
    name: "Lute",
    price: "35 gp",
    weightLb: 2,
    description: "String instrument commonly carried by bards.",
  },
  {
    name: "Fine clothes",
    price: "15 gp",
    weightLb: 6,
    description: "Formal clothing meant for social occasions.",
  },
  {
    name: "Common clothes",
    price: "0.5 gp",
    weightLb: 3,
    description: "Simple everyday clothing.",
  },
  {
    name: "Traveler's clothes",
    price: "2 gp",
    weightLb: 4,
    description: "Sturdy clothes suited for long journeys.",
  },
  {
    name: "Disguise kit",
    price: "25 gp",
    weightLb: 3,
    description: "Makeup, costumes, and props for disguises.",
  },
  {
    name: "Con tools",
    price: null,
    weightLb: 5,
    description: "Miscellaneous props used to support deception schemes.",
  },
  {
    name: "Artisan's tools",
    price: "5 gp",
    weightLb: 5,
    description: "General trade tools for a chosen craft.",
  },
  {
    name: "Herbalism kit",
    price: "5 gp",
    weightLb: 3,
    description: "Pouches and clippers used to gather and prepare herbs.",
  },
  {
    name: "Shovel",
    price: "2 gp",
    weightLb: 5,
    description: "Simple digging tool.",
  },
  {
    name: "Iron pot",
    price: "2 gp",
    weightLb: 10,
    description: "Heavy cooking pot for camp meals.",
  },
  {
    name: "Letter of introduction",
    price: null,
    weightLb: null,
    description: "Letter used to establish identity or recommendation.",
  },
  {
    name: "Scroll case",
    price: "1 gp",
    weightLb: 0.5,
    description: "Protective case for maps, scrolls, or documents.",
  },
  {
    name: "Winter blanket",
    price: "0.5 gp",
    weightLb: 3,
    description: "Thick blanket for cold weather travel.",
  },
];
