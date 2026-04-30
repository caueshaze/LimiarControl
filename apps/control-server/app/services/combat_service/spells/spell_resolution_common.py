from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session

from app.models.combat import CombatState
from app.services.combat_service.exceptions import CombatServiceError
from app.schemas.roll import RollResult


@dataclass
class SpellResolutionResult:
    roll_result: RollResult | None = None
    roll_total: int | None = None
    is_critical: bool = False
    is_hit: bool | None = None
    is_saved: bool | None = None
    target_ac: int | None = None
    base_ac: int | None = None
    base_save_dc: int | None = None
    cover: object = None
    cover_modifier: int = 0
    effective_dc: int = 0
    pending_spell_id: str | None = None
    pending_save_id: str | None = None
    damage: int = 0
    healing: int = 0
    new_hp: int | None = None
    effect_msg: str = ""
    previous_hp: int | None = None
    concentration_check: dict | None = None
    rolled_effect_total: int | None = None
    adv_ctx: object = None
    vis_ctx: object = None


class SpellResolutionCommonMixin:
    @classmethod
    def _normalize_pending_target_variant_assignments(
        cls,
        raw_assignments: object,
    ) -> list[dict]:
        if not isinstance(raw_assignments, list):
            return []
        normalized: list[dict] = []
        seen_target_ids: set[str] = set()
        for entry in raw_assignments:
            if not isinstance(entry, dict):
                continue
            target_participant_id = entry.get("target_participant_id")
            variant_key = entry.get("variant_key")
            if not isinstance(target_participant_id, str) or not target_participant_id.strip():
                raise CombatServiceError(
                    "Modal pending state is missing target_participant_id in a variant assignment.",
                    400,
                )
            if not isinstance(variant_key, str) or not variant_key.strip():
                raise CombatServiceError(
                    "Modal pending state is missing variant_key in a target assignment.",
                    400,
                )
            normalized_target_id = target_participant_id.strip()
            if normalized_target_id in seen_target_ids:
                raise CombatServiceError(
                    f"Duplicate modal pending variant assignment for participant {normalized_target_id}.",
                    400,
                )
            seen_target_ids.add(normalized_target_id)
            normalized.append(
                {
                    "target_participant_id": normalized_target_id,
                    "variant_key": variant_key.strip(),
                    "variant_label": entry.get("variant_label"),
                    "target_ref_id": entry.get("target_ref_id"),
                }
            )
        return normalized

    @classmethod
    def _find_pending_target_variant_assignment(
        cls,
        pending_payload: dict,
        *,
        target_participant_id: str | None,
    ) -> dict | None:
        if not isinstance(target_participant_id, str):
            return None
        assignments = cls._normalize_pending_target_variant_assignments(
            pending_payload.get("target_variant_assignments")
        )
        for assignment in assignments:
            if assignment["target_participant_id"] == target_participant_id:
                return assignment
        return None

    @classmethod
    def _build_pending_modal_payload(
        cls,
        spell_context: dict,
        target_p: dict,
    ) -> dict:
        target_participant_id = target_p.get("id")
        target_variant_assignments = cls._normalize_pending_target_variant_assignments(
            spell_context.get("target_variant_assignments")
        )
        manual_notes_by_target = [
            entry
            for entry in (spell_context.get("manual_notes_by_target") or [])
            if isinstance(entry, dict)
        ]
        effects = spell_context.get("effects")
        on_end_effects = spell_context.get("on_end_effects")

        if target_variant_assignments:
            assignment = cls._find_pending_target_variant_assignment(
                {"target_variant_assignments": target_variant_assignments},
                target_participant_id=target_participant_id,
            )
            if assignment is None:
                raise CombatServiceError(
                    f"Missing modal variant assignment for target participant {target_participant_id}.",
                    400,
                )
            return {
                "variant_scope": "per_target",
                "selected_variant_key": assignment["variant_key"],
                "selected_variant_label": assignment.get("variant_label"),
                "target_variant_assignments": target_variant_assignments,
                "manual_notes_by_target": manual_notes_by_target,
                "effects": list(effects or []),
                "on_end_effects": list(on_end_effects or []),
            }

        selected_variant_key = spell_context.get("selected_variant_key")
        if isinstance(selected_variant_key, str) and selected_variant_key.strip():
            return {
                "variant_scope": "single_target",
                "selected_variant_key": selected_variant_key.strip(),
                "selected_variant_label": spell_context.get("selected_variant_label"),
                "target_variant_assignments": [
                    {
                        "target_participant_id": target_participant_id,
                        "target_ref_id": target_p.get("ref_id"),
                        "variant_key": selected_variant_key.strip(),
                        "variant_label": spell_context.get("selected_variant_label"),
                    }
                ]
                if isinstance(target_participant_id, str)
                else None,
                "manual_notes_by_target": manual_notes_by_target,
                "effects": list(effects or []),
                "on_end_effects": list(on_end_effects or []),
            }

        return {}

    @classmethod
    def _build_pending_spell_context_from_payload(
        cls,
        pending_payload: dict,
        *,
        target_participant: dict | None,
    ) -> dict:
        spell_context = {
            "spell_name": pending_payload.get("spell_name"),
            "spell_canonical_key": pending_payload.get("spell_canonical_key"),
            "concentration": bool(pending_payload.get("concentration")),
            "effects": list(pending_payload.get("effects") or []),
            "on_end_effects": list(pending_payload.get("on_end_effects") or []),
            "selected_variant_key": pending_payload.get("selected_variant_key"),
            "selected_variant_label": pending_payload.get("selected_variant_label"),
            "target_variant_assignments": pending_payload.get("target_variant_assignments"),
            "manual_notes_by_target": pending_payload.get("manual_notes_by_target"),
        }
        variant_scope = pending_payload.get("variant_scope")
        if variant_scope != "per_target":
            return spell_context

        target_participant_id = (
            target_participant.get("id") if isinstance(target_participant, dict) else None
        )
        assignment = cls._find_pending_target_variant_assignment(
            pending_payload,
            target_participant_id=target_participant_id,
        )
        if assignment is None:
            raise CombatServiceError(
                f"Pending modal spell is missing a variant assignment for target participant {target_participant_id}.",
                400,
            )
        spell_context["selected_variant_key"] = assignment["variant_key"]
        spell_context["selected_variant_label"] = assignment.get("variant_label")
        return spell_context

    @classmethod
    def _format_manual_notes_for_log(cls, manual_notes_by_target: object) -> str:
        if not isinstance(manual_notes_by_target, list):
            return ""
        chunks: list[str] = []
        for entry in manual_notes_by_target:
            if not isinstance(entry, dict):
                continue
            target_name = entry.get("target_display_name") or "Target"
            notes = entry.get("manual_notes")
            if not isinstance(notes, list) or not notes:
                continue
            labels = [
                note.get("label")
                for note in notes
                if isinstance(note, dict) and isinstance(note.get("label"), str)
            ]
            if labels:
                chunks.append(f"{target_name}: {', '.join(labels)}")
        return f" Notas manuais: {'; '.join(chunks)}." if chunks else ""

    @classmethod
    def _apply_spell_effect(
        cls,
        db: Session,
        state: CombatState,
        target_ref_id: str,
        target_kind: str,
        effect_kind: str,
        amount: int,
        *,
        damage_type: str | None = None,
        is_critical: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
    ) -> tuple[int | None, str, int | None, dict | None]:
        if amount <= 0:
            return None, "", None, None
        if effect_kind == "healing":
            new_hp, effect_msg, previous_hp = cls._apply_healing_to_target(db, target_ref_id, target_kind, amount, state)
            return new_hp, effect_msg, previous_hp, None
        return cls._apply_damage_to_target(
            db,
            target_ref_id,
            target_kind,
            amount,
            damage_type=damage_type,
            is_crit=is_critical,
            state=state,
            **cls._build_concentration_roll_kwargs(concentration_roll_source, concentration_manual_roll),
        )

    @classmethod
    def _build_pending_spell_payload(
        cls,
        spell_context: dict,
        target_p: dict,
        *,
        action_kind: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None = None,
        is_saved: bool | None = None,
        is_critical: bool = False,
        roll_total: int | None = None,
        roll_result: RollResult | None = None,
        target_ac: int | None = None,
        effective_dc: int | None = None,
    ) -> dict:
        base = {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": action_kind,
            "effect_kind": effect_kind,
            "effect_dice": spell_context["effect_dice"],
            "effect_bonus": effect_bonus,
            "damage_type": spell_context.get("damage_type"),
            "elemental_affinity_eligible": spell_context.get("elemental_affinity_eligible"),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "target_ref_id": target_p["ref_id"],
            "target_kind": target_p["kind"],
            "target_display_name": target_p["display_name"],
            "save_ability": spell_context.get("save_ability"),
            "save_dc": effective_dc if effective_dc is not None else spell_context.get("save_dc"),
            "is_critical": is_critical,
            "roll": roll_total,
            "roll_result": roll_result.model_dump(mode="json") if roll_result else None,
            **cls._build_pending_modal_payload(spell_context, target_p),
        }
        if target_ac is not None:
            base["target_ac"] = target_ac
        if save_success_outcome is not None:
            base["save_success_outcome"] = save_success_outcome
        if is_saved is not None:
            base["is_saved"] = is_saved
        return base
