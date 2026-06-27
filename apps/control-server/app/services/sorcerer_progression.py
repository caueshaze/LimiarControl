from __future__ import annotations

from app.services.draconic_ancestry import (
    normalize_subclass_config,
    resolve_draconic_lineage_state,
)


DRACONIC_BLOODLINE_SUBCLASS_ID = "draconic_bloodline"

SORCERY_POINTS_RESOURCE_KEY = "sorceryPoints"


def _normalize_class_id(value: object) -> str:
    return str(value or "").strip().lower()


def _safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback


def compute_sorcery_points_max(level: object) -> int:
    """Font of Magic (PHB 2014): a sorcerer gains sorcery points equal to their
    sorcerer level, starting at level 2. Levels below 2 have no points."""
    normalized_level = max(0, _safe_int(level, 0))
    return normalized_level if normalized_level >= 2 else 0


def apply_sorcery_points_canonical_state(data: dict | None) -> dict:
    """Populate (and clamp) the sorcery-point pool in ``classResources``.

    ``pointsMax`` is derived from the sorcerer level; ``pointsRemaining`` is
    preserved across recomputes and clamped to ``[0, pointsMax]``. Merges into
    any existing ``classResources`` so sibling resources (e.g. the Dragonborn
    breath weapon) are left untouched.
    """
    next_data = dict(data) if isinstance(data, dict) else {}
    class_resources_raw = next_data.get("classResources")
    class_resources: dict = dict(class_resources_raw) if isinstance(class_resources_raw, dict) else {}

    if not is_sorcerer_class(next_data.get("class")):
        class_resources.pop(SORCERY_POINTS_RESOURCE_KEY, None)
    else:
        points_max = compute_sorcery_points_max(next_data.get("level", 1))
        if points_max <= 0:
            class_resources.pop(SORCERY_POINTS_RESOURCE_KEY, None)
        else:
            existing = class_resources.get(SORCERY_POINTS_RESOURCE_KEY)
            existing_remaining = (
                _safe_int(existing.get("usesRemaining"), points_max)
                if isinstance(existing, dict)
                else points_max
            )
            class_resources[SORCERY_POINTS_RESOURCE_KEY] = {
                "usesMax": points_max,
                "usesRemaining": max(0, min(existing_remaining, points_max)),
            }

    if class_resources:
        next_data["classResources"] = class_resources
    else:
        next_data.pop("classResources", None)
    return next_data


def get_sorcery_points_remaining(data: dict | None) -> int:
    payload = data if isinstance(data, dict) else {}
    class_resources = payload.get("classResources")
    if not isinstance(class_resources, dict):
        return 0
    resource = class_resources.get(SORCERY_POINTS_RESOURCE_KEY)
    if not isinstance(resource, dict):
        return 0
    return max(0, _safe_int(resource.get("usesRemaining"), 0))


def is_sorcerer_class(value: object) -> bool:
    return _normalize_class_id(value) == "sorcerer"


def is_draconic_bloodline_sorcerer(data: dict | None) -> bool:
    payload = dict(data) if isinstance(data, dict) else {}
    return is_sorcerer_class(payload.get("class")) and payload.get("subclass") == DRACONIC_BLOODLINE_SUBCLASS_ID


def get_draconic_resilience_hit_point_bonus(data: dict | None) -> int:
    payload = dict(data) if isinstance(data, dict) else {}
    if not is_draconic_bloodline_sorcerer(payload):
        return 0
    return max(0, int(payload.get("level", 1) or 1))


def build_sorcerer_class_features(data: dict | None) -> list[dict]:
    next_data = dict(data) if isinstance(data, dict) else {}
    if not is_sorcerer_class(next_data.get("class")):
        return []

    level = max(1, int(next_data.get("level", 1) or 1))
    subclass = next_data.get("subclass")
    if subclass != DRACONIC_BLOODLINE_SUBCLASS_ID:
        return []

    lineage = resolve_draconic_lineage_state(next_data)
    features: list[dict] = []

    features.append(
        {
            "id": "draconic_resilience",
            "source": "subclass",
            "levelGranted": 1,
            "label": "Resiliência Dracônica",
            "description": "Seu máximo de pontos de vida aumenta em 1 por nível de feiticeiro e, sem armadura, sua CA base é 13 + Destreza.",
            "kind": "passive",
            "metadata": {
                "sourceKey": "sorcerer_draconic_bloodline",
                "grantsHpPerSorcererLevel": 1,
                "grantsUnarmoredAcFormula": True,
                "acFormula": "13_plus_dex",
                "requiresNoArmor": True,
            },
        }
    )

    if lineage["ancestry"] and lineage["damageType"]:
        features.append(
            {
                "id": "draconic_ancestry",
                "source": "subclass",
                "levelGranted": 1,
                "label": f"Ancestral Dracônico: {lineage.get('ancestryLabel') or lineage['ancestry']}",
                "description": "A linhagem dracônica define o tipo de dano e a resistência futura da subclasse.",
                "kind": "subclass",
                "metadata": {
                    "ancestry": lineage["ancestry"],
                    "damageType": lineage["damageType"],
                    "resistanceType": lineage["resistanceType"],
                },
            }
        )

    if lineage["hasElementalAffinity"] and lineage["damageType"] and lineage["resistanceType"]:
        features.append(
            {
                "id": "elemental_affinity",
                "source": "subclass",
                "levelGranted": 6,
                "label": "Afinidade Elemental",
                "description": "Magias do tipo da linhagem ficam elegíveis ao bônus de Carisma e concedem resistência associada.",
                "kind": "passive",
                "metadata": {
                    "ancestry": lineage["ancestry"],
                    "damageType": lineage["damageType"],
                    "resistanceType": lineage["resistanceType"],
                    "damageBonusAbility": "charisma",
                    "grantsResistanceAtLevel": 6,
                },
            }
        )

    if level >= 14:
        features.append(
            {
                "id": "dragon_wings",
                "source": "subclass",
                "levelGranted": 14,
                "label": "Asas Dracônicas",
                "description": "Como ação bônus, faça crescer asas dracônicas e ganhe velocidade de voo igual à sua velocidade de caminhada, até dispensá-las como ação bônus.",
                "kind": "activated",
                "metadata": {
                    "activationCost": "bonus_action",
                    "grantsFlight": True,
                },
            }
        )

    return features


def apply_sorcerer_canonical_state(data: dict | None) -> dict:
    next_data = dict(data) if isinstance(data, dict) else {}
    if not is_sorcerer_class(next_data.get("class")):
        return next_data

    next_data["subclassConfig"] = normalize_subclass_config(
        next_data.get("subclass"),
        next_data.get("subclassConfig"),
    )
    if next_data.get("subclass") == DRACONIC_BLOODLINE_SUBCLASS_ID:
        next_data["classFeatures"] = build_sorcerer_class_features(next_data)
    else:
        next_data["classFeatures"] = []
    next_data = apply_sorcery_points_canonical_state(next_data)
    return next_data
