from __future__ import annotations

from app.services.draconic_ancestry import (
    normalize_subclass_config,
    resolve_draconic_lineage_state,
)


DRACONIC_BLOODLINE_SUBCLASS_ID = "draconic_bloodline"


def _normalize_class_id(value: object) -> str:
    return str(value or "").strip().lower()


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
    return next_data
