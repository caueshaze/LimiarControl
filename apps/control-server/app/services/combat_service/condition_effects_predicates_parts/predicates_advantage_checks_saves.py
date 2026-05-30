from __future__ import annotations

import logging
from typing import Literal

from app.schemas.campaign_entity_shared import AbilityName

from .predicates_creature_language import get_participant_creature_type
from .predicates_encumbrance_movement import get_participant_encumbrance_tier
from .predicates_spell_metadata import _declarative_effect_group_key
from .predicates_visibility_conditions import combine_advantage_modes

logger = logging.getLogger(__name__)

_ENCUMBRANCE_AFFECTING_ABILITIES = frozenset({"strength", "dexterity", "constitution"})


def resolve_check_advantage_mode(
    participant: dict,
    ability: AbilityName,
    skill: str | None = None,
    target_participant_id: str | None = None,
    manual_mode: Literal["advantage", "normal", "disadvantage"] = "normal",
) -> Literal["advantage", "normal", "disadvantage"]:
    automatic_mode = "normal"
    active_effects = participant.get("active_effects") or []
    logger.info(
        "[resolve_check_advantage_mode] participant_id=%s ability=%s skill=%s target_participant_id=%s active_effects_count=%s",
        participant.get("id") or participant.get("ref_id"),
        ability,
        skill,
        target_participant_id,
        len(active_effects),
    )
    matched = 0
    seen_keys: set[str] = set()
    for effect in active_effects:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue

        effect_type = declarative.get("type")
        params = declarative.get("params")
        if not isinstance(effect_type, str):
            continue
        if not isinstance(params, dict) or params.get("ability") != ability:
            continue

        against = params.get("against")
        if against == "selected_target" and target_participant_id != metadata.get("selected_target_participant_id"):
            continue

        dedup_key = f"{_declarative_effect_group_key(metadata, effect, effect_type, ability)}|{effect_type}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        if effect_type == "advantage_on_checks":
            automatic_mode = combine_advantage_modes(automatic_mode, "advantage")
            matched += 1
        elif effect_type == "disadvantage_on_checks":
            automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")
            matched += 1
    encumbrance_tier = get_participant_encumbrance_tier(participant)
    if encumbrance_tier in ("heavily_encumbered", "overloaded") and ability in _ENCUMBRANCE_AFFECTING_ABILITIES:
        automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")

    final = combine_advantage_modes(manual_mode, automatic_mode)
    logger.info(
        "[resolve_check_advantage_mode] matched=%s manual_mode=%s automatic_mode=%s final=%s",
        matched,
        manual_mode,
        automatic_mode,
        final,
    )
    return final


def explain_check_modifier_sources(
    participant: dict,
    *,
    ability: AbilityName,
    roll_type: Literal["ability", "skill"] = "ability",
    skill: str | None = None,
    target_participant_id: str | None = None,
) -> list[dict]:
    explanations: list[dict] = []
    active_effects = participant.get("active_effects") or []
    logger.info(
        "[explain_check_modifier_sources] participant_id=%s ability=%s roll_type=%s skill=%s target_participant_id=%s active_effects_count=%s",
        participant.get("id") or participant.get("ref_id"),
        ability,
        roll_type,
        skill,
        target_participant_id,
        len(active_effects),
    )
    seen_keys: set[str] = set()
    for effect in active_effects:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue

        effect_type = declarative.get("type")
        if effect_type not in {"advantage_on_checks", "disadvantage_on_checks"}:
            continue

        params = declarative.get("params")
        if not isinstance(params, dict):
            continue

        dedup_key = f"{_declarative_effect_group_key(metadata, effect, effect_type, params.get('ability', ''))}|{effect_type}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        against = params.get("against") if params.get("against") in {"any", "effect_target", "selected_target"} else "any"
        effect_ability = params.get("ability")
        modifier_type = "advantage" if effect_type == "advantage_on_checks" else "disadvantage"
        entry = {
            "source_label": metadata.get("source_spell_name") or effect.get("display_label") or "Spell effect",
            "modifier_type": modifier_type,
            "roll_type": roll_type,
            "ability": effect_ability if isinstance(effect_ability, str) else None,
            "skill": skill if roll_type == "skill" else None,
            "against": against,
            "selected_target_participant_id": metadata.get("selected_target_participant_id")
            if isinstance(metadata.get("selected_target_participant_id"), str)
            else None,
            "selected_target_display_name": metadata.get("selected_target_display_name")
            if isinstance(metadata.get("selected_target_display_name"), str)
            else None,
            "applied": False,
            "skip_reason": None,
        }

        if effect_ability != ability:
            entry["skip_reason"] = "skill_mismatch" if roll_type == "skill" else "ability_mismatch"
            explanations.append(entry)
            continue

        if against == "selected_target":
            selected_target_id = metadata.get("selected_target_participant_id")
            if not isinstance(target_participant_id, str) or not target_participant_id.strip():
                entry["skip_reason"] = "missing_target"
                explanations.append(entry)
                continue
            if target_participant_id != selected_target_id:
                entry["skip_reason"] = "target_mismatch"
                explanations.append(entry)
                continue

        entry["applied"] = True
        explanations.append(entry)
    encumbrance_tier = get_participant_encumbrance_tier(participant)
    if encumbrance_tier in ("heavily_encumbered", "overloaded") and ability in _ENCUMBRANCE_AFFECTING_ABILITIES:
        explanations.append({
            "source_label": "Carga",
            "modifier_type": "disadvantage",
            "roll_type": roll_type,
            "ability": ability,
            "skill": skill if roll_type == "skill" else None,
            "against": "any",
            "selected_target_participant_id": None,
            "selected_target_display_name": None,
            "applied": True,
            "skip_reason": None,
            "reason": "encumbrance",
        })

    logger.info(
        "[explain_check_modifier_sources] explanations_count=%s applied_count=%s",
        len(explanations),
        sum(1 for e in explanations if e.get("applied")),
    )
    return explanations


def resolve_saving_throw_advantage_from_effects(
    participant: dict,
    *,
    source_participant: dict | None = None,
    ability: str | None = None,
) -> dict:
    adv: set[str] = set()
    dis: set[str] = set()
    consume_effect_ids: list[str] = []

    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue

        declarative = metadata.get("declarative_save_effect")
        if not isinstance(declarative, dict):
            continue
        if declarative.get("type") != "saving_throw_advantage_against_creature_types":
            continue

        params = declarative.get("params")
        if not isinstance(params, dict):
            continue
        roll_types = params.get("roll_types")
        if isinstance(roll_types, list) and "saving_throw" not in roll_types:
            continue
        mode = str(params.get("mode") or "").strip().lower()
        if mode not in {"advantage", "disadvantage"}:
            continue

        required_types = params.get("source_creature_types")
        if isinstance(required_types, list) and required_types:
            if source_participant is None:
                continue
            source_type = get_participant_creature_type(source_participant)
            allowed = {str(t).strip().lower() for t in required_types if t}
            if source_type not in allowed:
                continue

        source_label = str(params.get("source") or "").strip() or str(metadata.get("source_spell_key") or "").strip() or "saving_throw_advantage"
        if mode == "advantage":
            adv.add(source_label)
        else:
            dis.add(source_label)

        if params.get("consume_on_apply") is True:
            effect_id = effect.get("id")
            if isinstance(effect_id, str) and effect_id and effect_id not in consume_effect_ids:
                consume_effect_ids.append(effect_id)

    return {
        "advantage_sources": sorted(adv),
        "disadvantage_sources": sorted(dis),
        "consume_effect_ids": consume_effect_ids,
    }


def _get_save_declarative_context(
    participant: dict,
    ability: AbilityName,
    *,
    source_participant: dict | None = None,
) -> tuple[str, list[str], list[str], list[dict]]:
    automatic_mode = "normal"
    adv_strs: list[str] = []
    dis_strs: list[str] = []
    details: list[dict] = []
    seen_keys: set[str] = set()

    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "spell_effect":
            continue
        metadata = effect.get("metadata")
        if not isinstance(metadata, dict):
            continue
        declarative = metadata.get("declarative_effect")
        if not isinstance(declarative, dict):
            continue

        effect_type = declarative.get("type")
        if effect_type not in {"advantage_on_saves", "disadvantage_on_saves"}:
            continue

        params = declarative.get("params")
        if not isinstance(params, dict):
            continue
        abilities = params.get("abilities")
        if not isinstance(abilities, list) or ability not in abilities:
            continue

        dedup_key = f"{_declarative_effect_group_key(metadata, effect, effect_type, ability)}|{effect_type}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        source_label = metadata.get("source_spell_name") or effect.get("display_label") or "Spell effect"
        if effect_type == "advantage_on_saves":
            automatic_mode = combine_advantage_modes(automatic_mode, "advantage")
            adv_strs.append(source_label)
            details.append({"source_label": source_label, "modifier_type": "advantage", "roll_type": "save", "ability": ability, "applied": True, "skip_reason": None})
        elif effect_type == "disadvantage_on_saves":
            automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")
            dis_strs.append(source_label)
            details.append({"source_label": source_label, "modifier_type": "disadvantage", "roll_type": "save", "ability": ability, "applied": True, "skip_reason": None})

    source_ctx = resolve_saving_throw_advantage_from_effects(participant, source_participant=source_participant, ability=ability)
    for source_label in source_ctx["advantage_sources"]:
        automatic_mode = combine_advantage_modes(automatic_mode, "advantage")
        adv_strs.append(source_label)
        details.append({"source_label": source_label, "modifier_type": "advantage", "roll_type": "save", "ability": ability, "applied": True, "skip_reason": None})
    for source_label in source_ctx["disadvantage_sources"]:
        automatic_mode = combine_advantage_modes(automatic_mode, "disadvantage")
        dis_strs.append(source_label)
        details.append({"source_label": source_label, "modifier_type": "disadvantage", "roll_type": "save", "ability": ability, "applied": True, "skip_reason": None})

    return automatic_mode, adv_strs, dis_strs, details
