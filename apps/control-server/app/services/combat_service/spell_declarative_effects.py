from __future__ import annotations

from typing import Literal
from uuid import uuid4

from app.schemas.base_spell import SpellDeclarativeEffect
from app.schemas.campaign_entity_shared import AbilityName, SKILL_ABILITY_MAP, SkillName
from .condition_effects_predicates import (
    explain_check_modifier_sources,
    resolve_check_advantage_mode,
)
from .exceptions import CombatServiceError


class CombatSpellDeclarativeEffectsMixin:
    @classmethod
    def _normalize_declarative_effects(cls, raw_effects: object) -> list[SpellDeclarativeEffect]:
        if not isinstance(raw_effects, list):
            return []
        normalized: list[SpellDeclarativeEffect] = []
        for entry in raw_effects:
            if not isinstance(entry, dict):
                continue
            normalized.append(SpellDeclarativeEffect.model_validate(entry))
        return normalized

    @classmethod
    def _spell_context_declarative_effects(cls, spell_context: dict) -> list[SpellDeclarativeEffect]:
        return cls._normalize_declarative_effects(spell_context.get("effects"))

    @classmethod
    def _spell_context_on_end_effects(cls, spell_context: dict) -> list[SpellDeclarativeEffect]:
        return cls._normalize_declarative_effects(spell_context.get("on_end_effects"))

    @classmethod
    def _spell_context_has_declarative_effects(cls, spell_context: dict) -> bool:
        return bool(cls._spell_context_declarative_effects(spell_context))

    @classmethod
    def _resolve_declarative_effect_target(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        effect: SpellDeclarativeEffect,
        metadata: dict,
    ) -> dict | None:
        participant_id = (
            metadata.get("selected_target_participant_id")
            if effect.target == "selected_target"
            else metadata.get("caster_participant_id")
        )
        if isinstance(participant_id, str):
            found = cls._find_participant_by_id(state, participant_id)
            if found is not None:
                return found
        if effect.target == "selected_target" and target_participant is None:
            raise CombatServiceError(
                "Declarative spell effect requires a selected target.", 400
            )
        if effect.target == "caster":
            return attacker
        return target_participant

    @classmethod
    def _declarative_duration_kwargs(
        cls,
        *,
        effect: SpellDeclarativeEffect,
        attacker: dict,
        target_participant: dict | None,
    ) -> dict:
        duration = effect.duration
        if duration is None:
            return {
                "duration_type": "manual",
                "remaining_rounds": None,
                "expires_at_participant_id": None,
            }
        anchor = duration.anchor or "target"
        expires_at = (
            attacker.get("id")
            if anchor == "caster"
            else target_participant.get("id") if isinstance(target_participant, dict) else None
        )
        return {
            "duration_type": duration.type,
            "remaining_rounds": duration.rounds,
            "expires_at_participant_id": expires_at,
        }

    @classmethod
    def _replace_matching_effects(cls, participant: dict, effect_type: str, params: dict) -> None:
        keep: list[dict] = []
        for existing in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(existing)
            declarative = metadata.get("declarative_effect")
            if (
                isinstance(declarative, dict)
                and declarative.get("type") == effect_type
                and declarative.get("params") == params
            ):
                continue
            keep.append(existing)
        cls._set_participant_effects(participant, keep)

    @classmethod
    def _apply_single_declarative_effect(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        spell_context: dict,
        effect: SpellDeclarativeEffect,
        effect_group_id: str,
        on_end_effects: list[SpellDeclarativeEffect],
    ) -> list[dict]:
        metadata = {
            "declarative_effect_group_id": effect_group_id,
            "declarative_effect": effect.model_dump(mode="json"),
            "declarative_on_end_effects": [
                entry.model_dump(mode="json") for entry in on_end_effects
            ],
            "caster_participant_id": attacker.get("id"),
            "selected_target_participant_id": target_participant.get("id")
            if isinstance(target_participant, dict)
            else None,
            "selected_target_ref_id": target_participant.get("ref_id")
            if isinstance(target_participant, dict)
            else None,
            "selected_target_display_name": target_participant.get("display_name")
            if isinstance(target_participant, dict)
            else None,
            "source_spell_key": spell_context.get("spell_canonical_key"),
            "source_spell_name": spell_context.get("spell_name"),
            "selected_variant_key": spell_context.get("selected_variant_key"),
            "selected_variant_label": spell_context.get("selected_variant_label"),
            "target_assignment_source": spell_context.get("variant_scope"),
            "context_origin": spell_context.get("context_origin") or "initial_cast",
            "concentration": bool(spell_context.get("concentration")),
            "concentration_group": effect_group_id if spell_context.get("concentration") else None,
        }
        resolved_target = cls._resolve_declarative_effect_target(
            state=state,
            attacker=attacker,
            target_participant=target_participant,
            effect=effect,
            metadata=metadata,
        )
        if resolved_target is None:
            return []
        metadata["effect_target_participant_id"] = resolved_target.get("id")
        metadata["effect_target_ref_id"] = resolved_target.get("ref_id")
        metadata["effect_target_display_name"] = resolved_target.get("display_name")

        params = effect.params.model_dump(mode="json")
        if effect.type in {"advantage_on_checks", "disadvantage_on_checks"}:
            metadata["against"] = params.get("against") or "any"
        if effect.stacking == "replace":
            cls._replace_matching_effects(resolved_target, effect.type, params)

        duration_kwargs = cls._declarative_duration_kwargs(
            effect=effect,
            attacker=attacker,
            target_participant=resolved_target,
        )

        created: list[dict] = []
        if effect.type == "apply_condition":
            active_effect = cls._build_active_effect(
                kind="condition",
                source_participant_id=attacker.get("id"),
                condition_type=params["condition"],
                metadata=metadata,
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        elif effect.type == "modify_stat":
            active_effect = cls._build_active_effect(
                kind=params["stat"],
                source_participant_id=attacker.get("id"),
                numeric_value=params["value"],
                metadata=metadata,
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        else:
            active_effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker.get("id"),
                metadata={**metadata, **params},
                display_label=spell_context.get("spell_name"),
                **duration_kwargs,
            )
            cls._append_effect_to_participant(resolved_target, active_effect)
            created.append(active_effect)
        return created

    @classmethod
    def _apply_declarative_spell_effects(
        cls,
        *,
        state,
        attacker: dict,
        target_participant: dict | None,
        spell_context: dict,
        effect_group_id: str | None = None,
    ) -> dict:
        effects = cls._spell_context_declarative_effects(spell_context)
        on_end_effects = cls._spell_context_on_end_effects(spell_context)
        if not effects:
            return {"applied_effects": [], "effect_group_id": None}

        effect_group_id = effect_group_id or str(uuid4())
        applied: list[dict] = []
        for effect in effects:
            applied.extend(
                cls._apply_single_declarative_effect(
                    state=state,
                    attacker=attacker,
                    target_participant=target_participant,
                    spell_context=spell_context,
                    effect=effect,
                    effect_group_id=effect_group_id,
                    on_end_effects=on_end_effects,
                )
            )
        return {"applied_effects": applied, "effect_group_id": effect_group_id}

    @classmethod
    def _execute_on_end_effects_for_removed(
        cls,
        *,
        state,
        removed_effects: list[dict],
    ) -> list[dict]:
        executed: list[dict] = []
        processed_groups: set[str] = set()
        for removed in removed_effects:
            metadata = cls._get_effect_metadata(removed)
            group_id = metadata.get("declarative_effect_group_id")
            if isinstance(group_id, str) and group_id in processed_groups:
                continue
            if isinstance(group_id, str):
                processed_groups.add(group_id)

            raw_on_end = metadata.get("declarative_on_end_effects")
            if not isinstance(raw_on_end, list) or not raw_on_end:
                continue

            caster = cls._find_participant_by_id(state, metadata.get("caster_participant_id"))
            target = cls._find_participant_by_id(
                state, metadata.get("selected_target_participant_id")
            )
            if caster is None:
                continue

            pseudo_context = {
                "spell_canonical_key": metadata.get("source_spell_key"),
                "spell_name": metadata.get("source_spell_name"),
                "concentration": False,
            }
            for effect in cls._normalize_declarative_effects(raw_on_end):
                executed.extend(
                    cls._apply_single_declarative_effect(
                        state=state,
                        attacker=caster,
                        target_participant=target,
                        spell_context=pseudo_context,
                        effect=effect,
                        effect_group_id=str(uuid4()),
                        on_end_effects=[],
                    )
                )
        return executed

    @classmethod
    async def _cast_spell_via_declarative_effects(
        cls,
        db,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state,
        spell_context: dict,
        target_participant: dict | None,
        effect_group_id: str | None = None,
    ) -> dict | None:
        if not cls._spell_context_has_declarative_effects(spell_context):
            return None

        application = cls._apply_declarative_spell_effects(
            state=state,
            attacker=attacker,
            target_participant=target_participant,
            spell_context=spell_context,
            effect_group_id=effect_group_id,
        )
        applied_effects = application["applied_effects"]
        summary_target = target_participant or attacker
        summary_text = (
            f"{spell_context['spell_name']} aplicou {len(applied_effects)} efeito(s)."
            if applied_effects
            else f"{spell_context['spell_name']} nao aplicou efeitos."
        )
        return cls._base_spell_result(
            spell_name=spell_context["spell_name"],
            spell_context=spell_context,
            target_display_name=summary_target.get("display_name") or "Target",
            target_kind=summary_target.get("kind") or "player",
            action_kind=spell_context.get("spell_mode") or "utility",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_context['spell_name']} em "
                f"{summary_target.get('display_name') or 'Target'}."
            ),
            extra={
                "__declarative_effect_group_id": application["effect_group_id"],
                "__applied_effect_count": len(applied_effects),
                "concentration_group": application["effect_group_id"]
                if spell_context.get("concentration")
                else None,
            },
        )

    @classmethod
    def _resolve_check_advantage_mode_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
        target_participant_id: str | None = None,
    ) -> str:
        state = cls.get_state(db, session_id)
        if state is None:
            return "normal"
        participant = next(
            (
                entry
                for entry in state.participants
                if entry.get("kind") == actor_kind and entry.get("ref_id") == actor_ref_id
            ),
            None,
        )
        if not isinstance(participant, dict):
            return "normal"
        return resolve_check_advantage_mode(participant, ability, target_participant_id=target_participant_id)

    @classmethod
    def _resolve_skill_check_advantage_mode_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        skill: SkillName,
        target_participant_id: str | None = None,
    ) -> str:
        return cls._resolve_check_advantage_mode_for_actor(
            db,
            session_id,
            actor_kind=actor_kind,
            actor_ref_id=actor_ref_id,
            ability=SKILL_ABILITY_MAP[skill],
            target_participant_id=target_participant_id,
        )

    @classmethod
    def _explain_check_modifier_sources_for_actor(
        cls,
        db,
        session_id: str,
        *,
        actor_kind: str,
        actor_ref_id: str,
        ability: AbilityName,
        roll_type: Literal["ability", "skill"] = "ability",
        skill: SkillName | None = None,
        target_participant_id: str | None = None,
    ) -> list[dict]:
        state = cls.get_state(db, session_id)
        if state is None:
            return []
        participant = next(
            (
                entry
                for entry in state.participants
                if entry.get("kind") == actor_kind and entry.get("ref_id") == actor_ref_id
            ),
            None,
        )
        if not isinstance(participant, dict):
            return []
        return explain_check_modifier_sources(
            participant,
            ability=ability,
            roll_type=roll_type,
            skill=skill,
            target_participant_id=target_participant_id,
        )
