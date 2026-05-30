from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollActorStats
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_attack_base
from ...exceptions import CombatServiceError

_PRODUCE_FLAME_DURATION_SECONDS = 600
_PRODUCE_FLAME_BRIGHT_LIGHT_METERS = 3
_PRODUCE_FLAME_DIM_LIGHT_METERS = 3
_PRODUCE_FLAME_THROW_RANGE_METERS = 9


class ProduceFlameAutomationMixin:
    @classmethod
    def _remove_existing_produce_flame_effects(
        cls,
        participant: dict,
    ) -> list[dict]:
        effects = cls._get_participant_effects(participant)
        if not effects:
            return []
        removed: list[dict] = []
        kept: list[dict] = []
        for effect in effects:
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "produce_flame"
            ):
                removed.append(effect)
                continue
            kept.append(effect)
        if removed:
            cls._set_participant_effects(participant, kept)
        return removed

    @classmethod
    def _find_produce_flame_effect(
        cls,
        participant: dict,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "produce_flame"
            ):
                return effect
        return None

    @classmethod
    async def _cast_produce_flame_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        spell_mode = cls._normalize_lookup(spell_context.get("spell_mode")).replace(" ", "_")
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        if spell_mode == "utility":
            removed = cls._remove_existing_produce_flame_effects(attacker)
            damage_dice = spell_context.get("damage_preview") or spell_context.get("effect_dice") or "1d8"
            effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + _PRODUCE_FLAME_DURATION_SECONDS,
                metadata={
                    "source_spell_key": "produce_flame",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": True,
                    "narrative": True,
                    "visual": True,
                    "visible_to_all": True,
                    "utility": "produce_flame",
                    "creates_light": True,
                    "bright_light_meters": _PRODUCE_FLAME_BRIGHT_LIGHT_METERS,
                    "dim_light_meters": _PRODUCE_FLAME_DIM_LIGHT_METERS,
                    "can_throw": True,
                    "throw_range_meters": _PRODUCE_FLAME_THROW_RANGE_METERS,
                    "throw_attack_type": "ranged_spell",
                    "damage_dice": damage_dice,
                    "damage_type": "Fire",
                    "resolved_at_character_level": cls._safe_int(
                        cls._as_dict(attacker_model.state_json).get("level"),
                        cls._safe_int(attacker.get("level"), 1),
                    ),
                },
                display_label=spell_name,
            )
            cls._append_effect_to_participant(attacker, effect)
            flag_modified(state, "participants")
            summary = f"{spell_name}: chama criada na sua mão por 10 minutos."
            if removed:
                summary = f"{spell_name}: chama anterior substituída."
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=attacker["display_name"],
                target_kind=attacker["kind"],
                summary_text=summary,
                log_message=f"{attacker['display_name']} conjurou {spell_name} e criou uma chama na mão.",
                extra={
                    "created_effect_id": effect["id"],
                },
            )

        if spell_mode == "spell_attack":
            active_effect = cls._find_produce_flame_effect(attacker)
            if not isinstance(target_participant, dict):
                raise CombatServiceError("Criar Chamas (arremesso) exige alvo.", 400)
            if active_effect is None:
                raise CombatServiceError(
                    "Criar Chamas não está ativo no conjurador para arremessar.",
                    400,
                )
            metadata = cls._get_effect_metadata(active_effect)
            damage_dice = metadata.get("damage_dice")
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                damage_dice = spell_context.get("effect_dice") or "1d8"
            damage_dice = damage_dice.strip()

            _, target_ac, *_ = cls._get_stats(
                db,
                target_participant["ref_id"],
                target_participant["kind"],
                session_id,
                combat_state=state,
            )
            roll_result = resolve_attack_base(
                RollActorStats(
                    display_name=attacker["display_name"],
                    abilities={},
                    actor_kind="player",
                    actor_ref_id=attacker["ref_id"],
                ),
                bonus_override=cls._safe_int(spell_context.get("attack_bonus"), 0),
                target_ac=target_ac or 10,
                roll_source=getattr(req, "roll_source", "system"),
                manual_roll=getattr(req, "manual_roll", None),
                manual_rolls=getattr(req, "manual_rolls", None),
                has_advantage=bool(getattr(req, "has_advantage", False)),
                has_disadvantage=bool(getattr(req, "has_disadvantage", False)),
            )
            roll_result.is_gm_roll = is_gm
            is_hit = bool(roll_result.success)
            damage = 0
            new_hp = None
            if is_hit:
                _, rolled_damage = cls._resolve_damage_roll(
                    damage_dice,
                    roll_source=getattr(req, "roll_source", "system"),
                    manual_roll=None,
                    manual_rolls=None,
                )
                damage = max(0, rolled_damage)
                new_hp, _, _, _ = cls._apply_spell_effect(
                    db,
                    state,
                    target_participant["ref_id"],
                    target_participant["kind"],
                    "damage",
                    damage,
                    damage_type="Fire",
                    is_critical=roll_result.selected_roll == 20,
                    attacker_participant_id=attacker.get("id"),
                )

            cls._consume_effect_ids(attacker, [active_effect.get("id")])
            flag_modified(state, "participants")

            target_name = target_participant.get("display_name") or target_participant.get("ref_id") or "Alvo"
            if is_hit:
                summary = f"{spell_name}: chama arremessada acertou {target_name} ({damage} de dano de fogo)."
            else:
                summary = f"{spell_name}: chama arremessada errou {target_name}."
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant.get("kind") or "session_entity",
                action_kind="spell_attack",
                summary_text=summary,
                log_message=(
                    f"{attacker['display_name']} arremessou {spell_name} em {target_name}."
                ),
                extra={
                    "is_hit": is_hit,
                    "roll": roll_result.total if roll_result else None,
                    "roll_result": roll_result,
                    "target_ac": target_ac,
                    "damage": damage,
                    "new_hp": new_hp,
                },
            )

        raise CombatServiceError(
            "Criar Chamas suporta apenas os modos utility e spell_attack.",
            400,
        )
