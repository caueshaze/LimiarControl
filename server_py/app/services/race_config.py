from app.services.dragonborn_ancestry import is_valid_dragonborn_ancestry

GNOME_SUBRACES = {"forest", "rock"}
HALF_ELF_ABILITY_CHOICES = {
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
}
SKILL_NAMES = {
    "acrobatics",
    "animalHandling",
    "arcana",
    "athletics",
    "deception",
    "history",
    "insight",
    "intimidation",
    "investigation",
    "medicine",
    "nature",
    "perception",
    "performance",
    "persuasion",
    "religion",
    "sleightOfHand",
    "stealth",
    "survival",
}
LEGACY_RACE_ALIASES = {
    "forest-gnome": {"race": "gnome", "raceConfig": {"gnomeSubrace": "forest"}},
    "rock-gnome": {"race": "gnome", "raceConfig": {"gnomeSubrace": "rock"}},
}


def _normalize_unique_string_list(value: object, allowed_values: set[str], limit: int) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for entry in value:
        if not isinstance(entry, str) or entry not in allowed_values or entry in seen:
            continue
        normalized.append(entry)
        seen.add(entry)
        if len(normalized) >= limit:
            break
    return normalized


def normalize_race_state(race: object, race_config: object):
    normalized_race = race if isinstance(race, str) else ""
    normalized_config = race_config if isinstance(race_config, dict) else {}

    legacy = LEGACY_RACE_ALIASES.get(normalized_race)
    if legacy:
        normalized_race = legacy["race"]
        normalized_config = {**normalized_config, **legacy["raceConfig"]}

    if normalized_race == "dragonborn":
        ancestry = normalized_config.get("dragonbornAncestry")
        return {
            "race": normalized_race,
            "raceConfig": {
                "dragonbornAncestry": ancestry if is_valid_dragonborn_ancestry(ancestry) else None,
            },
        }

    if normalized_race == "gnome":
        subrace = normalized_config.get("gnomeSubrace")
        return {
            "race": normalized_race,
            "raceConfig": {
                "gnomeSubrace": subrace if isinstance(subrace, str) and subrace in GNOME_SUBRACES else None,
            },
        }

    if normalized_race == "half-elf":
        return {
            "race": normalized_race,
            "raceConfig": {
                "halfElfAbilityChoices": _normalize_unique_string_list(
                    normalized_config.get("halfElfAbilityChoices"),
                    HALF_ELF_ABILITY_CHOICES,
                    2,
                ),
                "halfElfSkillChoices": _normalize_unique_string_list(
                    normalized_config.get("halfElfSkillChoices"),
                    SKILL_NAMES,
                    2,
                ),
            },
        }

    return {"race": normalized_race, "raceConfig": None}


def validate_race_state(data: object) -> tuple[bool, str | None]:
    if not isinstance(data, dict):
        return False, "Character sheet payload must be an object"

    normalized = normalize_race_state(data.get("race"), data.get("raceConfig"))
    race = normalized["race"]
    race_config = normalized["raceConfig"] or {}

    if race == "dragonborn" and not is_valid_dragonborn_ancestry(race_config.get("dragonbornAncestry")):
        return False, "Dragonborn characters require a valid dragonborn ancestry"

    if race == "gnome":
        subrace = race_config.get("gnomeSubrace")
        if not isinstance(subrace, str) or subrace not in GNOME_SUBRACES:
            return False, "Gnome characters require a valid gnome subrace"

    if race == "half-elf":
        ability_choices = race_config.get("halfElfAbilityChoices")
        skill_choices = race_config.get("halfElfSkillChoices")
        if not isinstance(ability_choices, list) or len(ability_choices) != 2:
            return False, "Half-elf characters require exactly two racial ability choices"
        if len(set(ability_choices)) != 2 or any(choice not in HALF_ELF_ABILITY_CHOICES for choice in ability_choices):
            return False, "Half-elf racial ability choices must be distinct and cannot include charisma"
        if not isinstance(skill_choices, list) or len(skill_choices) != 2:
            return False, "Half-elf characters require exactly two racial skill choices"
        if len(set(skill_choices)) != 2 or any(choice not in SKILL_NAMES for choice in skill_choices):
            return False, "Half-elf racial skill choices must be distinct and valid"

    return True, None
