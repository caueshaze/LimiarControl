from __future__ import annotations

from typing import Any

from app.services.combat_service.cover_modifiers import cover_label

from ..exceptions import CombatServiceError


class SpellResponseMixin:

    @classmethod
    def _build_multi_instance_log_message(
        cls,
        *,
        attacker: dict,
        spell_context: dict,
        outcomes: list[dict],
        was_overridden: bool,
        action_cost: str,
    ) -> str:
        spell_name = spell_context["spell_name"]
        damage_type = spell_context.get("damage_type") or "energia"
        n = len(outcomes)

        lines = [f"{attacker['display_name']} conjurou {spell_name}: {n} instâncias."]
        for o in outcomes:
            idx = o["instance_index"]
            name = o["target_display_name"]
            dmg = o["damage"]
            o_cover_modifier = o.get("cover_modifier", 0)
            o_cover = o.get("cover")
            if o.get("is_hit") is False:
                if o_cover_modifier > 0 and o_cover and cover_label(o_cover):
                    lines.append(
                        f"  Instância {idx} → {name}: {o.get('roll', '?')} vs AC efetiva {o.get('effective_ac')} (base {o.get('base_ac')} + {cover_label(o_cover)}) - errou."
                    )
                else:
                    lines.append(f"  Instância {idx} → {name}: errou.")
            elif dmg > 0:
                lines.append(f"  Instância {idx} → {name}: {dmg} de dano de {damage_type}.")
            else:
                lines.append(f"  Instância {idx} → {name}: sem dano.")

        log_message = "\n".join(lines)
        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(spell_context.get('target_variant_assignments'), spell_context.get('manual_notes_by_target'))}"
            f"{cls._format_manual_notes_for_log(spell_context.get('manual_notes_by_target'))}"
            f"{cls._format_concentration_group_for_log(spell_context.get('concentration_group'))}"
        ).strip()
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        return log_message

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
            if result.cover_modifier > 0 and cover_label(result.cover):
                cover_text = f" (AC efetiva {result.target_ac or 10}, base {result.base_ac} + {cover_label(result.cover)})"
            else:
                cover_text = ""
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
            ac_display = f"AC {result.target_ac or 10}" if not cover_text else ""
            if result.is_hit:
                log_message = (
                    f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"{result.roll_total} total vs {ac_display}{cover_text}{adv_text}{vis_text} - acerto."
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
                    f"{result.roll_total} total vs {ac_display}{cover_text}{adv_text}{vis_text} - errou."
                )
        elif spell_mode == "saving_throw":
            if result.pending_save_id:
                log_message = (
                    f"{attacker['display_name']} lancou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"aguardando teste de {spell_context['save_ability']} contra CD {result.effective_dc} (GM resolve)."
                )
            else:
                save_text = "passou" if result.is_saved else "falhou"
                if result.cover_modifier > 0 and cover_label(result.cover):
                    cover_text = f" (CD efetiva {result.effective_dc}, base {result.base_save_dc} - {cover_label(result.cover)})"
                else:
                    cover_text = ""
                dc_display = f"CD {result.effective_dc}" if not cover_text else ""
                log_message = (
                    f"{attacker['display_name']} lancou {spell_context['spell_name']} em {target_p['display_name']}: "
                    f"alvo {save_text} no save de {spell_context['save_ability']} contra {dc_display}{cover_text}."
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

        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(spell_context.get('target_variant_assignments'), spell_context.get('manual_notes_by_target'))}"
            f"{cls._format_manual_notes_for_log(spell_context.get('manual_notes_by_target'))}"
            f"{cls._format_concentration_group_for_log(spell_context.get('concentration_group'))}"
        ).strip()

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
        if automation_result is not None:
            response_save_dc = automation_result.get("save_dc")
        elif spell_mode == "saving_throw":
            response_save_dc = result.effective_dc
        else:
            response_save_dc = spell_context.get("save_dc")

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": (
                automation_result.get("selected_variant_key")
                if automation_result is not None
                else spell_context.get("selected_variant_key")
            ),
            "selected_variant_label": (
                automation_result.get("selected_variant_label")
                if automation_result is not None
                else spell_context.get("selected_variant_label")
            ),
            "context_origin": (
                automation_result.get("context_origin")
                if automation_result is not None
                else spell_context.get("context_origin") or "initial_cast"
            ),
            "concentration_group": (
                automation_result.get("concentration_group")
                if automation_result is not None
                else spell_context.get("concentration_group")
            ),
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
            "cover": result.cover if isinstance(result.cover, str) else None,
            "base_ac": result.base_ac,
            "base_save_dc": result.base_save_dc,
            "cover_modifier": result.cover_modifier,
            "target_display_name": target_display_name,
            "target_kind": target_kind,
            "save_ability": spell_context.get("save_ability"),
            "save_dc": response_save_dc,
            "save_success_outcome": save_success_outcome,
            "effect_dice": effect_dice,
            "effect_bonus": resp_effect_bonus,
            "pending_spell_id": result.pending_spell_id,
            "pending_save_id": result.pending_save_id,
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
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": [],
            "target_variant_assignments": (
                automation_result.get("target_variant_assignments")
                if automation_result is not None
                else spell_context.get("target_variant_assignments")
            ),
            "manual_notes_by_target": (
                automation_result.get("manual_notes_by_target")
                if automation_result is not None
                else spell_context.get("manual_notes_by_target")
            ),
            "applied_declarative_effects_by_target": (
                automation_result.get("applied_declarative_effects_by_target")
                if automation_result is not None
                else None
            ),
        }
