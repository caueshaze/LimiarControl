from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .condition_effects_predicates import has_condition


@dataclass
class AttackAdvantageContext:
    advantage_sources: list[str] = field(default_factory=list)
    disadvantage_sources: list[str] = field(default_factory=list)
    consumed_effect_ids_on_roll: list[str] = field(default_factory=list)
    result: Literal["advantage", "normal", "disadvantage"] = "normal"

    def describe(self) -> str:
        has_adv = bool(self.advantage_sources)
        has_dis = bool(self.disadvantage_sources)
        if self.result == "normal" and has_adv and has_dis:
            adv_str = ", ".join(self.advantage_sources)
            dis_str = ", ".join(self.disadvantage_sources)
            return f"normal ({adv_str} canceled by {dis_str})"
        sources = self.advantage_sources if self.result == "advantage" else self.disadvantage_sources
        return f"{self.result} ({', '.join(sources)})" if sources else self.result


def resolve_attack_advantage(attacker: dict, target: dict, attack_kind: str = "melee") -> AttackAdvantageContext:
    adv: list[str] = []
    dis: list[str] = []
    consume_effect_ids: list[str] = []
    if has_condition(attacker, "prone"):
        dis.append("attacker_prone")
    if has_condition(attacker, "frightened"):
        dis.append("attacker_frightened")
    if has_condition(attacker, "restrained"):
        dis.append("attacker_restrained")
    if has_condition(attacker, "poisoned"):
        dis.append("attacker_poisoned")
    if has_condition(attacker, "invisible"):
        adv.append("attacker_invisible")
    if has_condition(target, "restrained"):
        adv.append("target_restrained")
    if has_condition(target, "paralyzed"):
        adv.append("target_paralyzed")
    if has_condition(target, "stunned"):
        adv.append("target_stunned")
    if has_condition(target, "unconscious"):
        adv.append("target_unconscious")
    if has_condition(target, "invisible"):
        dis.append("target_invisible")
    if has_condition(target, "prone"):
        if attack_kind == "melee":
            adv.append("target_prone_melee")
        elif attack_kind == "ranged":
            dis.append("target_prone_ranged")
    # Guiding Bolt rider: target carries a spell_effect that grants advantage
    # to the next attack roll against this specific participant and is consumed
    # only after a valid attack roll is resolved.
    target_id = target.get("id")
    if isinstance(target_id, str) and target_id:
        for effect in target.get("active_effects") or []:
            if effect.get("kind") != "spell_effect":
                continue
            metadata = effect.get("metadata")
            if not isinstance(metadata, dict):
                continue
            declarative = metadata.get("declarative_effect")
            if not isinstance(declarative, dict):
                continue
            if declarative.get("type") != "attack_advantage_against_target":
                continue
            params = declarative.get("params")
            if not isinstance(params, dict):
                continue
            if params.get("mode") != "advantage":
                continue
            roll_types = params.get("roll_types")
            if not isinstance(roll_types, list) or "attack" not in roll_types:
                continue
            if params.get("applies_to_attackers") != "any":
                continue
            marked_target = metadata.get("marked_target_participant_id")
            if isinstance(marked_target, str) and marked_target != target_id:
                continue
            adv.append(metadata.get("source_spell_name") or "Guiding Bolt")
            if params.get("consume_on_apply") is True:
                effect_id = effect.get("id")
                if isinstance(effect_id, str) and effect_id and effect_id not in consume_effect_ids:
                    consume_effect_ids.append(effect_id)
    if adv and not dis:
        result: Literal["advantage", "normal", "disadvantage"] = "advantage"
    elif dis and not adv:
        result = "disadvantage"
    else:
        result = "normal"
    return AttackAdvantageContext(
        advantage_sources=adv,
        disadvantage_sources=dis,
        consumed_effect_ids_on_roll=consume_effect_ids,
        result=result,
    )


def get_attack_advantage_penalty(attacker: dict, target: dict) -> int:
    ctx = resolve_attack_advantage(attacker, target, attack_kind="melee")
    if ctx.result == "advantage":
        return 1
    if ctx.result == "disadvantage":
        return -1
    return 0


def get_attack_auto_crit(attacker: dict, target: dict, attack_kind: str = "melee") -> str:  # noqa: ARG001
    if attack_kind != "melee":
        return ""
    if has_condition(target, "paralyzed"):
        return "target_paralyzed"
    if has_condition(target, "unconscious"):
        return "target_unconscious"
    return ""


def resolve_spell_attack_kind(spell_or_action: dict | None = None) -> str:  # noqa: ARG001
    return "ranged"


def get_effective_reach(base_reach_cells: int, *, effective_size: str | None = None) -> int:
    from .reach import get_effective_reach as _reach
    from .entity_size import normalize_size_category

    size_cat = normalize_size_category(effective_size) if effective_size is not None else None
    return _reach(base_reach_cells, effective_size=size_cat)
