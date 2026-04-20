from __future__ import annotations

from typing import Any

from app.services.combat_service.cover_modifiers import cover_label

from ..exceptions import CombatServiceError


class SpellResponseMixin:

    @classmethod
    def _build_cast_log_message(
        cls,
        *,
        attacker: dict,
        target_p: dict,
        spell_context: dict,
        spell_mode: str,
        effect_kind: str | None,
        result,
        save_success_outcome: str | None,
        was_overridden: bool,
        action_cost: str,
        custom_log_message: str | None,
    ) -> str:
        if isinstance(custom_log_message, str) and custom_log_message.strip():
            log_message = custom_log_message.strip()
        elif spell_mode == "spell_attack":
            cover_text = (
                f" ({cover_label(result.cover)})" if cover_label(result.cover) else ""
            )
            adv_text = ""
            if result.adv_ctx is not None and (
                result.adv_ctx.advantage_sources or result.adv_ctx.disadvantage_sources
            ):
                adv_text = f" [{result.adv_ctx.describe()}]"
            vis_text = ""
            if result.vis_ctx is not None and not result.vis_ctx.is_directly_visible:
                vis_text = (
                    f" [Target not directly visible: {result.vis_ctx.describe()}]"
                )
            if result.is_hit:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{result.roll_total} total vs AC {result.target_ac or 10}{cover_text}{adv_text}{vis_text} - acerto."
                )
                if result.pending_spell_id:
                    log_message += " Efeito pendente."
                elif result.damage > 0:
                    log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                elif result.healing > 0:
                    log_message += (
                        f" {result.healing} HP restaurados{result.effect_msg}"
                    )
            else:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{result.roll_total} total vs AC {result.target_ac or 10}{cover_text}{adv_text}{vis_text} - errou."
                )
        elif spell_mode == "saving_throw":
            save_text = "passou" if result.is_saved else "falhou"
            cover_text = (
                f" ({cover_label(result.cover)})" if cover_label(result.cover) else ""
            )
            log_message = (
                f"{attacker['display_name']} lancou {spell_context['spell_name']} em {target_p['display_name']}: "
                f"alvo {save_text} no save de {spell_context['save_ability']} contra CD {result.effective_dc}{cover_text}."
            )
            if result.pending_spell_id:
                if result.is_saved and save_success_outcome == "half_damage":
                    log_message += " Dano pendente para aplicar metade."
                else:
                    log_message += " Efeito pendente."
            elif effect_kind == "damage":
                if result.is_saved and save_success_outcome == "half_damage":
                    log_message += (
                        f" Dano rolado {result.rolled_effect_total or 0}; dano aplicado {result.damage} de "
                        f"{spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                    )
                elif result.damage > 0:
                    log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"
                else:
                    log_message += " Nenhum dano aplicado."
        elif effect_kind == "healing":
            log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            if result.pending_spell_id:
                log_message += " Cura pendente."
            else:
                log_message += f" {result.healing} HP restaurados{result.effect_msg}"
        else:
            log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}."
            if result.pending_spell_id:
                log_message += " Dano pendente."
            else:
                log_message += f" {result.damage} de dano de {spell_context.get('damage_type') or 'energia'}{result.effect_msg}"

        if isinstance(result.concentration_check, dict) and isinstance(
            result.concentration_check.get("summary_text"), str
        ):
            log_message = (
                f"{log_message} {result.concentration_check['summary_text']}".strip()
            )

        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"

        return log_message

    @classmethod
    def _build_cast_response(
        cls,
        *,
        spell_context: dict,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None,
        result,
        automation_result: dict | None,
        target_p: dict,
        action_cost: str,
        summary_text: str | None,
        inventory_refresh_required: bool,
        was_overridden: bool,
    ) -> dict:
        damage_type = (
            automation_result.get("damage_type")
            if automation_result is not None
            else spell_context.get("damage_type")
        )
        target_display_name = (
            automation_result.get("target_display_name")
            if automation_result is not None
            else target_p["display_name"]
        )
        target_kind = (
            automation_result.get("target_kind")
            if automation_result is not None
            else target_p["kind"]
        )
        effect_dice = (
            automation_result.get("effect_dice")
            if automation_result is not None
            else spell_context.get("effect_dice")
        )
        resp_effect_bonus = (
            automation_result.get("effect_bonus")
            if automation_result is not None
            else effect_bonus
        )

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": effect_kind,
            "damage": result.damage,
            "healing": result.healing,
            "damage_type": damage_type,
            "is_critical": result.is_critical,
            "is_hit": result.is_hit,
            "is_saved": result.is_saved,
            "new_hp": result.new_hp,
            "roll": result.roll_total,
            "roll_result": result.roll_result,
            "target_ac": result.target_ac,
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": resp_effect_bonus,
            "pending_spell_id": result.pending_spell_id,
            "effect_roll_required": bool(result.pending_spell_id),
            "base_effect": (
                automation_result.get("base_effect")
                if automation_result is not None
                else (None if spell_context.get("effect_dice") else 0)
            ),
            "action_cost": action_cost,
            "summary_text": summary_text,
            "inventory_refresh_required": inventory_refresh_required,
            "concentration_check": result.concentration_check,
            "elemental_affinity_eligible": bool(
                spell_context.get("elemental_affinity_eligible")
            ),
            "elemental_affinity_damage_type": spell_context.get(
                "elemental_affinity_damage_type"
            ),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }
