from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollActorStats
from app.services.roll_resolution import resolve_attack_base
from ...condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from ...exceptions import CombatServiceError


class ChillTouchAutomationMixin:
    @classmethod
    async def _cast_chill_touch_automation(
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
        if target_participant is None:
            raise CombatServiceError("Toque Necrótico exige um alvo.", 400)

        spell_name = spell_context["spell_name"]
        damage_dice = spell_context.get("effect_dice") or "1d8"
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)

        _, target_ac, *_ = cls._get_stats(
            db, target_participant["ref_id"], target_participant["kind"],
            session_id, combat_state=state,
        )
        adv_ctx = resolve_attack_advantage(attacker, target_participant, resolve_spell_attack_kind())
        has_adv = getattr(req, "has_advantage", False) or bool(adv_ctx.advantage_sources)
        has_dis = getattr(req, "has_disadvantage", False) or bool(adv_ctx.disadvantage_sources)
        adv_mode = (
            "advantage" if has_adv and not has_dis
            else "disadvantage" if has_dis and not has_adv
            else "normal"
        )
        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
            target_ac=target_ac or 10,
            roll_source=getattr(req, "roll_source", "system"),
            manual_roll=getattr(req, "manual_roll", None),
            manual_rolls=getattr(req, "manual_rolls", None),
        )
        roll_result.is_gm_roll = is_gm
        if adv_ctx.consumed_effect_ids_on_roll:
            cls._consume_effect_ids(attacker, adv_ctx.consumed_effect_ids_on_roll)
            cls._consume_effect_ids(target_participant, adv_ctx.consumed_effect_ids_on_roll)
        is_hit = bool(roll_result.success)
        is_critical = roll_result.selected_roll == 20
        damage = 0
        new_hp = None

        if is_hit:
            _, raw_damage = cls._resolve_damage_roll(
                damage_dice,
                critical=is_critical,
                roll_source=getattr(req, "roll_source", "system"),
            )
            damage = max(0, raw_damage)
            new_hp, _, *_ = cls._apply_spell_effect(
                db, state,
                target_participant["ref_id"],
                target_participant["kind"],
                "damage",
                damage,
                damage_type="Necrotic",
                is_critical=is_critical,
                attacker_participant_id=attacker.get("id"),
            )
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="spell_effect",
                    source_participant_id=attacker["id"],
                    duration_type="until_turn_start",
                    expires_at_participant_id=attacker["id"],
                    metadata={
                        "source_spell_key": "chill_touch",
                        "prevent_healing": True,
                    },
                    display_label=spell_name,
                ),
            )
            creature_type = cls.resolve_effective_creature_type(db, session_id, target_participant)
            if creature_type == "undead":
                cls._append_effect_to_participant(
                    target_participant,
                    cls._build_active_effect(
                        kind="spell_effect",
                        source_participant_id=attacker["id"],
                        duration_type="until_turn_start",
                        expires_at_participant_id=attacker["id"],
                        metadata={
                            "source_spell_key": "chill_touch",
                            "declarative_effect": {
                                "type": "roll_disadvantage_modifier",
                                "params": {
                                    "mode": "disadvantage",
                                    "roll_types": ["attack"],
                                    "applies_when_attacking_participant_id": attacker["id"],
                                    "consume_on_apply": False,
                                    "source": "chill_touch",
                                },
                            },
                        },
                        display_label=spell_name,
                    ),
                )
            flag_modified(state, "participants")

        target_name = target_participant["display_name"]
        if is_hit:
            summary = (
                f"{spell_name} acertou {target_name} por {damage} de dano necrótico. "
                "Alvo não pode recuperar PV até o início do próximo turno do conjurador."
            )
            log = (
                f"{attacker['display_name']} conjurou {spell_name} e acertou {target_name}. "
                f"Dano: {damage} necrótico."
            )
        else:
            summary = f"{spell_name} errou {target_name}."
            log = f"{attacker['display_name']} conjurou {spell_name} e errou {target_name}."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="spell_attack",
            summary_text=summary,
            log_message=log,
            extra={
                "is_hit": is_hit,
                "is_critical": is_critical,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "damage": damage,
                "new_hp": new_hp,
                "target_ac": target_ac,
            },
        )
