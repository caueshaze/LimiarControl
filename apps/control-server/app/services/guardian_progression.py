from __future__ import annotations

from app.services.class_progression import get_spell_slots_for_class_level


_GUARDIAN_REQUIRED_SPELLS: tuple[dict, ...] = (
    {
        "id": "guardian-spell-hunters_mark",
        "canonicalKey": "hunters_mark",
        "name": "Hunter's Mark",
        "level": 1,
        "school": "Divination",
        "prepared": True,
        "notes": "",
    },
)


def _normalize_class_id(value: object) -> str:
    return str(value or "").strip().lower()


def is_guardian_class(value: object) -> bool:
    return _normalize_class_id(value) == "guardian"


def get_guardian_fixed_subclass(level: int) -> str | None:
    return "hunter" if level >= 3 else None


def get_guardian_fixed_fighting_style(level: int) -> str | None:
    return "archery" if level >= 2 else None


def _normalize_spell_lookup(value: object) -> str:
    return str(value or "").strip().lower()


def _coerce_spell_entry(raw_spell: object) -> dict | None:
    if not isinstance(raw_spell, dict):
        return None
    name = str(raw_spell.get("name") or "").strip()
    if not name:
        return None
    canonical_key = raw_spell.get("canonicalKey")
    return {
        **raw_spell,
        "id": str(raw_spell.get("id") or f"spell-{name.lower().replace(' ', '_')}"),
        "name": name,
        "canonicalKey": str(canonical_key).strip() if isinstance(canonical_key, str) and canonical_key.strip() else None,
        "level": int(raw_spell.get("level", 0) or 0),
        "school": str(raw_spell.get("school") or "Evocation"),
        "prepared": bool(raw_spell.get("prepared", True)),
        "notes": str(raw_spell.get("notes") or ""),
    }


def _merge_guardian_required_spells(existing_spells: object) -> list[dict]:
    merged: list[dict] = []
    seen_required: set[str] = set()

    if isinstance(existing_spells, list):
        for raw_spell in existing_spells:
            spell = _coerce_spell_entry(raw_spell)
            if spell is None:
                continue

            required_spell = None
            canonical_lookup = _normalize_spell_lookup(spell.get("canonicalKey"))
            name_lookup = _normalize_spell_lookup(spell.get("name"))
            for template in _GUARDIAN_REQUIRED_SPELLS:
                if canonical_lookup and canonical_lookup == template["canonicalKey"]:
                    required_spell = template
                    break
                if name_lookup and name_lookup == _normalize_spell_lookup(template["name"]):
                    required_spell = template
                    break

            if required_spell is None:
                merged.append(spell)
                continue

            canonical_key = required_spell["canonicalKey"]
            if canonical_key in seen_required:
                continue

            merged.append({
                **spell,
                "id": str(spell.get("id") or required_spell["id"]),
                "canonicalKey": canonical_key,
                "name": str(spell.get("name") or required_spell["name"]),
                "level": int(spell.get("level", required_spell["level"]) or required_spell["level"]),
                "school": str(spell.get("school") or required_spell["school"]),
                "prepared": True,
                "notes": str(spell.get("notes") or ""),
            })
            seen_required.add(canonical_key)

    for spell in _GUARDIAN_REQUIRED_SPELLS:
        if spell["canonicalKey"] in seen_required:
            continue
        merged.append(dict(spell))

    return merged


def build_guardian_class_features(level: int, subclass: str | None) -> list[dict]:
    features: list[dict] = []

    if level >= 1:
        features.extend([
            {
                "id": "favored_enemy_beasts",
                "source": "class",
                "levelGranted": 1,
                "label": "Inimigo Favorito: Feras",
                "description": "Inimigo favorito fixo do Guardião: feras.",
                "kind": "passive",
                "metadata": {"favoredEnemy": "beasts"},
            },
            {
                "id": "natural_explorer_forest",
                "source": "class",
                "levelGranted": 1,
                "label": "Explorador Natural: Floresta",
                "description": "Terreno favorecido fixo do Guardião: floresta.",
                "kind": "passive",
                "metadata": {"terrain": "forest"},
            },
        ])

    if level >= 2:
        features.extend([
            {
                "id": "fighting_style_archery",
                "source": "class",
                "levelGranted": 2,
                "label": "Estilo de Luta: Arqueria",
                "description": "Recebe +2 em jogadas de ataque com armas à distância.",
                "kind": "fighting_style",
                "metadata": {
                    "fightingStyle": "archery",
                    "attackBonus": 2,
                    "appliesTo": "ranged_weapon_attacks",
                },
            },
            {
                "id": "spellcasting_guardian",
                "source": "class",
                "levelGranted": 2,
                "label": "Conjuração",
                "description": "Conjuração de Guardião baseada em Sabedoria.",
                "kind": "spellcasting",
                "metadata": {
                    "spellcastingAbility": "wisdom",
                    "mechanicsFamily": "ranger",
                },
            },
        ])

    if level >= 3:
        features.append(
            {
                "id": "primeval_awareness",
                "source": "class",
                "levelGranted": 3,
                "label": "Consciência Primitiva",
                "description": "Consciência Primitiva conforme o material do Guardião.",
                "kind": "passive",
                "metadata": None,
            }
        )
        if subclass == "hunter":
            features.extend([
                {
                    "id": "subclass_hunter",
                    "source": "subclass",
                    "levelGranted": 3,
                    "label": "Caçador",
                    "description": "Subclasse fixa do Guardião no nível 3.",
                    "kind": "subclass",
                    "metadata": {"subclass": "hunter"},
                },
                {
                    "id": "hunter_colossus_slayer",
                    "source": "subclass",
                    "levelGranted": 3,
                    "label": "Assassino de Colossos",
                    "description": "Uma vez por turno, ao atingir com arma um alvo já ferido, causa +1d8.",
                    "kind": "passive",
                    "metadata": {
                        "damageDice": "1d8",
                        "oncePerTurn": True,
                        "trigger": "weapon_hit_target_below_max_hp",
                    },
                },
            ])

    if level >= 4:
        features.append(
            {
                "id": "asi_guardian_dexterity_2",
                "source": "class",
                "levelGranted": 4,
                "label": "Aumento de Atributo",
                "description": "Aumenta Destreza em +2 no nível 4.",
                "kind": "asi",
                "metadata": {"ability": "dexterity", "bonus": 2},
            }
        )

    return features


def _normalize_guardian_spell_slots(level: int, existing_slots: object) -> dict[str, dict[str, int]]:
    slot_table = get_spell_slots_for_class_level("guardian", level) or {}
    current_slots = dict(existing_slots) if isinstance(existing_slots, dict) else {}
    normalized: dict[str, dict[str, int]] = {}

    for slot_level, max_slots in slot_table.items():
        key = str(slot_level)
        raw_slot = current_slots.get(key)
        used = raw_slot.get("used", 0) if isinstance(raw_slot, dict) else 0
        normalized[key] = {
            "max": int(max_slots),
            "used": min(int(used or 0), int(max_slots)),
        }

    return normalized


def apply_guardian_canonical_state(
    data: dict | None,
    *,
    previous_level: int | None = None,
) -> dict:
    next_data = dict(data) if isinstance(data, dict) else {}
    next_data.setdefault("classFeatures", [])
    if not is_guardian_class(next_data.get("class")):
        return next_data

    level = max(1, int(next_data.get("level", 1) or 1))
    subclass = get_guardian_fixed_subclass(level)
    next_data["subclass"] = subclass
    next_data["fightingStyle"] = get_guardian_fixed_fighting_style(level)
    next_data["classFeatures"] = build_guardian_class_features(level, subclass)

    if previous_level is not None and previous_level < 4 <= level:
        abilities = dict(next_data.get("abilities") or {})
        dexterity = int(abilities.get("dexterity", 0) or 0)
        abilities["dexterity"] = dexterity + 2
        next_data["abilities"] = abilities

    if level >= 2:
        spellcasting = dict(next_data.get("spellcasting") or {})
        spellcasting["ability"] = "wisdom"
        spellcasting["mode"] = spellcasting.get("mode") or "known"
        spellcasting["slots"] = _normalize_guardian_spell_slots(level, spellcasting.get("slots"))
        spellcasting["spells"] = _merge_guardian_required_spells(spellcasting.get("spells"))
        next_data["spellcasting"] = spellcasting
    else:
        next_data["spellcasting"] = None

    return next_data
