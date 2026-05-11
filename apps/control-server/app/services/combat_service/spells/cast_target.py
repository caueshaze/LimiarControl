from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import select

from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession
from app.models.session_command_event import SessionCommandEvent
from app.schemas.base_spell import SpellVariant
from app.schemas.roll import RollActorStats
from app.services.combat_service.condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_inventory_item_charges_current,
)
from app.integrations import LimiarMapClientError

from ..combat_targeting import get_combat_targeting_service
from ..cover_modifiers import resolve_cover_modifier
from ..exceptions import CombatServiceError
from ..targeting_diagnostics import INVALID_TARGET_TYPE, MAP_UNREACHABLE, NO_LINE_OF_EFFECT, NO_LINE_OF_SIGHT, NOT_VISIBLE, TARGET_OUT_OF_REACH
from ..targeting_intent import SpellCastIntent
from ..targeting_result import TargetingResult
from .cast_target_commit import CastTargetCommitMixin
from .cast_target_effect import CastTargetEffectMixin
from .spell_resolution import SpellResolutionResult

logger = logging.getLogger(__name__)


def _resolve_instance_spatial_error_phrase(result: TargetingResult) -> str:
    diag = result.diagnostics
    if diag:
        if TARGET_OUT_OF_REACH in diag.failure_reasons:
            return "is out of range"
        if NO_LINE_OF_SIGHT in diag.failure_reasons:
            return "has blocked line of sight"
        if NO_LINE_OF_EFFECT in diag.failure_reasons:
            return "has blocked line of effect"
        if NOT_VISIBLE in diag.failure_reasons:
            return "is not visible"
    return result.failure_reason or "cannot be targeted"


class CastTargetMixin(CastTargetCommitMixin, CastTargetEffectMixin):
    @classmethod
    def _validate_spell_target_creature_type_restriction(
        cls,
        db,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict,
    ) -> None:
        spell_key = cls._normalize_lookup(spell_canonical_key).replace(" ", "_")
        if spell_key != "hold_person":
            return
        creature_type = cls.resolve_effective_creature_type(
            db,
            session_id,
            target_participant,
        )
        if creature_type is not None and creature_type != "humanoid":
            raise CombatServiceError("Hold Person can only target humanoids.", 400)

    @classmethod
    def _upsert_shield_temp_ac_effect(cls, participant: dict, *, source_participant_id: str | None) -> None:
        effects = cls._get_participant_effects(participant)
        kept = []
        for effect in effects:
            metadata = cls._as_dict(effect.get("metadata"))
            if effect.get("kind") == "temp_ac_bonus" and metadata.get("source_spell_key") == "shield":
                continue
            kept.append(effect)
        cls._set_participant_effects(participant, kept)
        cls._append_effect_to_participant(
            participant,
            cls._build_active_effect(
                kind="temp_ac_bonus",
                source_participant_id=source_participant_id,
                numeric_value=5,
                duration_type="until_turn_start",
                expires_at_participant_id=participant.get("id"),
                metadata={"source_spell_key": "shield"},
                display_label="Shield",
            ),
        )

    @classmethod
    def _is_shielded_for_magic_missile(cls, participant: dict | None) -> bool:
        if not isinstance(participant, dict):
            return False
        for effect in cls._get_participant_effects(participant):
            metadata = cls._as_dict(effect.get("metadata"))
            if effect.get("kind") == "temp_ac_bonus" and metadata.get("source_spell_key") == "shield":
                return True
        return False
    @classmethod
    async def _resolve_teleport_spell(
        cls, db, session_id, req, state, attacker, attacker_model, spell_context, actor_user_id, is_gm
    ):
        if req.anchor_cell is None:
            raise CombatServiceError("Teleport spells require a destination point.", 400)
        if not state.use_map:
            raise CombatServiceError("Teleport spells require a tactical map.", 400)

        destination_cell = {"x": req.anchor_cell.x, "y": req.anchor_cell.y}
        client = cls._build_limiar_map_client()
        try:
            movement = client.move_combatant(
                session_id=session_id,
                action_id=f"teleport:{uuid4()}",
                combatant_id=attacker["ref_id"],
                destination_cell=destination_cell,
            )
        except LimiarMapClientError as exc:
            raise CombatServiceError(f"Teleport is unavailable: {exc}", 503) from exc

        if not movement.is_valid:
            raise CombatServiceError(movement.reason or "Invalid teleport destination.", 400)

        slot_spent = False
        action_cost = spell_context.get("action_cost") or "bonus_action"
        was_overridden = cls._consume_turn_resource(
            attacker, action_cost, is_gm=is_gm, override_resource_limit=req.override_resource_limit
        )
        if isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} e se teleportou para "
            f"({destination_cell['x']}, {destination_cell['y']})."
        )
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {"message": log_message, "actorUserId": actor_user_id, "source": "gm_override" if is_gm else "player_turn"},
        )
        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "teleport",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": attacker.get("display_name"),
            "target_kind": attacker.get("kind"),
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": False,
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [attacker["ref_id"]],
            "affected_cells": [destination_cell],
            "area_target_outcomes": [],
            "target_count": 1,
            "destination_cell": destination_cell,
        }
    @classmethod
    def _map_spell_rejection_reason(cls, reason: str | None) -> str:
        if reason == TARGET_OUT_OF_REACH:
            return "out_of_range"
        if reason == NO_LINE_OF_SIGHT:
            return "blocked_line_of_sight"
        if reason == NO_LINE_OF_EFFECT:
            return "blocked_line_of_effect"
        if reason in (INVALID_TARGET_TYPE, "target_not_found"):
            return "invalid_target"
        if reason == MAP_UNREACHABLE:
            return "missing_map_data"
        return "invalid_target"

    @classmethod
    def _build_spell_rejection_message(
        cls,
        *,
        actor_name: str,
        spell_name: str,
        reason: str,
        target_name: str | None = None,
        instance_index: int | None = None,
        is_area: bool = False,
    ) -> str:
        subject = f"{actor_name} tentou conjurar {spell_name}"
        if instance_index is not None:
            subject = f"{subject}, mas Feixe {instance_index}"
            if target_name:
                subject = f"{subject} contra {target_name}"
        elif is_area:
            subject = f"{subject}, mas a origem da area"
        elif target_name:
            subject = f"{subject} em {target_name}"

        if reason == "blocked_line_of_sight":
            return f"{subject} estava sem linha de visao."
        if reason == "blocked_line_of_effect":
            return f"{subject} estava sem linha de efeito."
        if reason == "out_of_range":
            return f"{subject} estava fora do alcance."
        if reason == "missing_map_data":
            return f"{subject} nao pode ser resolvido por falta de dados do mapa."
        return f"{subject} tinha um alvo invalido."

    @classmethod
    def _record_spell_cast_rejected_activity(
        cls,
        db,
        *,
        session_id: str,
        actor_user_id: str,
        actor_ref_id: str,
        actor_display_name: str,
        spell_context: dict,
        reason: str,
        target_ref_id: str | None = None,
        target_display_name: str | None = None,
        instance_index: int | None = None,
        area_origin: dict | None = None,
    ) -> None:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            return
        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == actor_user_id,
            )
        ).first()
        if not member or not member.id:
            return

        message = cls._build_spell_rejection_message(
            actor_name=actor_display_name,
            spell_name=str(spell_context.get("spell_name") or "magia"),
            reason=reason,
            target_name=target_display_name,
            instance_index=instance_index,
            is_area=area_origin is not None,
        )
        payload = {
            "eventType": "spell_cast_rejected",
            "actorRefId": actor_ref_id,
            "actorDisplayName": actor_display_name,
            "spellId": spell_context.get("spell_canonical_key"),
            "spellName": spell_context.get("spell_name"),
            "targetRefId": target_ref_id,
            "targetDisplayName": target_display_name,
            "instanceIndex": instance_index,
            "areaOrigin": area_origin,
            "reason": reason,
            "message": message,
        }
        db.add(
            SessionCommandEvent(
                id=str(uuid4()),
                session_id=session_entry.id,
                user_id=actor_user_id,
                member_id=member.id,
                actor_name=actor_display_name,
                command_type="spell_cast_rejected",
                payload_json=payload,
            )
        )
        db.commit()

    @classmethod
    def _validate_cast_prerequisites(
        cls,
        db,
        session_id,
        req,
        actor_user_id,
        is_gm,
        *,
        clear_pending_attack: bool = True,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, req.actor_participant_id,
        )
        cls._require_actor_status(
            attacker, ("active",), "You can only cast a spell when active."
        )
        cls._require_action_capable(attacker)
        if attacker["kind"] != "player":
            raise CombatServiceError(
                "Only players can use this spell casting flow.", 400
            )

        attacker_state_check, *_ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        attacker_data_check = cls._as_dict(attacker_state_check.state_json)
        if cls._as_dict(attacker_data_check.get("wildShape")).get("active"):
            raise CombatServiceError("Cannot cast spells while in Wild Shape.", 400)

        if clear_pending_attack:
            had_pending = isinstance(attacker.get("pending_attack"), dict)
            cls._clear_participant_pending_attack(attacker)
            if had_pending:
                flag_modified(state, "participants")

        attacker_model, _, _, _, _, _ = cls._get_stats(
            db, attacker["ref_id"], attacker["kind"], session_id
        )
        return state, attacker, attacker_model

    @classmethod
    def _resolve_area_size_meters(cls, spell_context: dict) -> float | None:
        area_shape = spell_context.get("area_shape")
        if not area_shape:
            return None
        if area_shape in ("sphere", "cylinder"):
            value = spell_context.get("radius_meters")
        elif area_shape == "line":
            value = spell_context.get("length_meters")
        elif area_shape == "cube":
            value = spell_context.get("side_meters")
        elif area_shape == "cone":
            value = (
                spell_context.get("length_meters")
                or spell_context.get("radius_meters")
            )
        else:
            value = None
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _build_resolved_spell_context_response(cls, req, spell_context: dict) -> dict:
        resolution_type = spell_context.get("spell_mode")
        range_meters = spell_context.get("range_meters")
        try:
            range_meters_value = float(range_meters) if range_meters is not None else None
        except (TypeError, ValueError):
            range_meters_value = None
        return {
            "spell_id": req.spell_id or spell_context.get("spell_canonical_key"),
            "spell_canonical_key": spell_context.get("spell_canonical_key"),
            "campaign_spell_id": req.campaign_spell_id,
            "inventory_item_id": spell_context.get("inventory_item_id"),
            "spell_name": spell_context["spell_name"],
            "spell_level": cls._safe_int(spell_context.get("spell_level"), 0),
            "slot_level": spell_context.get("slot_level"),
            "max_targets": spell_context.get("max_targets"),
            "base_max_targets": spell_context.get("base_max_targets"),
            "target_type": spell_context.get("target_type"),
            "selection_type": spell_context.get("selection_type"),
            "area_shape": spell_context.get("area_shape"),
            "area_size_meters": cls._resolve_area_size_meters(spell_context),
            "range_meters": range_meters_value,
            "resolution_type": resolution_type,
            "requires_attack_roll": resolution_type == "spell_attack",
            "requires_saving_throw": resolution_type == "saving_throw",
            "save_ability": spell_context.get("save_ability"),
            "damage_type": spell_context.get("damage_type"),
            "damage_preview": spell_context.get("effect_dice"),
            "effect_instance_count": cls._safe_int(
                spell_context.get("effect_instance_count"),
                1,
            ),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "upcast_applied": bool(spell_context.get("upcast_applied")),
            "upcast_added_instances": cls._safe_int(
                spell_context.get("upcast_added_instances"),
                0,
            ),
            "upcast_instance_effect_dice": spell_context.get("upcast_instance_effect_dice"),
            "cover_applies_to_save": spell_context.get("cover_applies_to_save"),
            "variants": spell_context.get("variants"),
            "selected_variant_key": spell_context.get("selected_variant_key"),
            "target_variant_assignments": spell_context.get("target_variant_assignments"),
        }

    @classmethod
    def resolve_spell_context(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        _, attacker, attacker_model = cls._validate_cast_prerequisites(
            db,
            session_id,
            req,
            actor_user_id,
            is_gm,
            clear_pending_attack=False,
        )
        spell_context = cls._resolve_player_spell_context(
            db, session_id, attacker, attacker_model, req,
        )
        return cls._build_resolved_spell_context_response(req, spell_context)

    @classmethod
    def _get_spell_variants_map(cls, spell_context: dict) -> dict[str, SpellVariant]:
        variants = cls._normalize_spell_variants(spell_context.get("variant_definitions"))
        return {variant.key: variant for variant in variants}

    @classmethod
    def _participant_display_name(cls, participant: dict | None) -> str:
        if isinstance(participant, dict):
            return participant.get("display_name") or participant.get("ref_id") or "Target"
        return "Target"

    @classmethod
    def _build_variant_summary_for_target(
        cls,
        *,
        participant: dict,
        variant: SpellVariant,
    ) -> dict:
        return {
            "target_ref_id": participant.get("ref_id"),
            "target_participant_id": participant.get("id"),
            "target_display_name": cls._participant_display_name(participant),
            "variant_key": variant.key,
            "variant_label": variant.labelPt or variant.labelEn or variant.key,
            "manual_notes": [
                note.model_dump(mode="json") for note in (variant.manualNotes or [])
            ],
        }

    @classmethod
    def _merge_spell_context_with_variant(
        cls,
        *,
        spell_context: dict,
        variant: SpellVariant,
        participant: dict | None = None,
        target_variant_assignments: list[dict] | None = None,
    ) -> dict:
        merged = dict(spell_context)
        base_effects = list(spell_context.get("effects") or [])
        base_on_end_effects = list(spell_context.get("on_end_effects") or [])
        merged["effects"] = base_effects + [
            effect.model_dump(mode="json") for effect in (variant.effects or [])
        ]
        merged["on_end_effects"] = base_on_end_effects + [
            effect.model_dump(mode="json") for effect in (variant.onEndEffects or [])
        ]
        merged["selected_variant_key"] = variant.key
        merged["selected_variant_label"] = variant.labelPt or variant.labelEn or variant.key
        merged["variant_scope"] = (
            "per_target"
            if isinstance(target_variant_assignments, list) and len(target_variant_assignments) > 1
            else "single_target"
        )
        merged["context_origin"] = spell_context.get("context_origin") or "initial_cast"
        merged["manual_notes_by_target"] = (
            [cls._build_variant_summary_for_target(participant=participant, variant=variant)]
            if isinstance(participant, dict) and variant.manualNotes
            else []
        )
        merged["target_variant_assignments"] = target_variant_assignments
        return merged

    @classmethod
    def _validate_modal_target_variant_assignments(
        cls,
        *,
        req,
        spell_context: dict,
        state,
    ) -> list[dict] | None:
        variant_map = cls._get_spell_variants_map(spell_context)
        raw_assignments = list(getattr(req, "target_variant_assignments", None) or [])
        variant_key = getattr(req, "variant_key", None)

        if not variant_map:
            if raw_assignments or variant_key:
                raise CombatServiceError("This spell does not define variants.", 400)
            return None

        max_targets = cls._safe_int(spell_context.get("max_targets"), 1)
        if raw_assignments:
            if variant_key:
                raise CombatServiceError(
                    "variant_key cannot be combined with target_variant_assignments.",
                    400,
                )
            if len(raw_assignments) < 2:
                raise CombatServiceError(
                    "Single-target modal casts must use variant_key.",
                    400,
                )
            if max_targets > 0 and len(raw_assignments) > max_targets:
                raise CombatServiceError(
                    f"This spell can affect at most {max_targets} targets at this cast level.",
                    400,
                )
            seen_target_ids: set[str] = set()
            validated: list[dict] = []
            for assignment in raw_assignments:
                target_participant_id = assignment.target_participant_id
                if target_participant_id in seen_target_ids:
                    raise CombatServiceError(
                        f"Duplicate target variant assignment for participant {target_participant_id}.",
                        400,
                    )
                participant = cls._find_participant_by_id(state, target_participant_id)
                if participant is None:
                    raise CombatServiceError(
                        f"Unknown target participant '{target_participant_id}'.",
                        400,
                    )
                variant = variant_map.get(assignment.variant_key)
                if variant is None:
                    raise CombatServiceError(
                        f"Unknown spell variant '{assignment.variant_key}' for this spell.",
                        400,
                    )
                seen_target_ids.add(target_participant_id)
                validated.append(
                    {
                        "target_participant_id": target_participant_id,
                        "target_ref_id": participant.get("ref_id"),
                        "participant": participant,
                        "variant": variant,
                        "variant_key": variant.key,
                        "variant_label": variant.labelPt or variant.labelEn or variant.key,
                    }
                )
            return validated

        if not isinstance(variant_key, str) or not variant_key.strip():
            raise CombatServiceError(
                "This spell requires choosing a variant before casting.",
                400,
            )
        variant = variant_map.get(variant_key.strip())
        if variant is None:
            raise CombatServiceError(
                f"Unknown spell variant '{variant_key}' for this spell.",
                400,
            )
        return None

    @classmethod
    def _validate_modal_variant_spatial_targets(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        assignments: list[dict],
        session_id: str,
    ) -> dict[str, TargetingResult]:
        targeting_service = get_combat_targeting_service(state.use_map)
        results_by_participant_id: dict[str, TargetingResult] = {}

        for assignment in assignments:
            participant = assignment["participant"]
            target_ref_id = assignment["target_ref_id"]
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-variant:{participant.get('id')}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_ref_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                spell_mode=spell_context["spell_mode"],
                target_type=spell_context.get("target_type"),
                selection_type=spell_context.get("selection_type"),
                attack_type=spell_context.get("attack_type"),
                range_kind=spell_context.get("range_kind"),
                area_shape=spell_context.get("area_shape"),
                range_meters=spell_context.get("range_meters"),
                requires_sight=bool(spell_context.get("requires_target_sight")),
                requires_effect=bool(spell_context.get("requires_target_effect")),
            )
            result = targeting_service.validate(intent, state)
            if not result.is_valid:
                diag = result.diagnostics
                reason = cls._map_spell_rejection_reason(
                    diag.primary_failure() if diag else None
                )
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=attacker.get("actor_user_id"),
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=reason,
                    target_ref_id=target_ref_id,
                    target_display_name=cls._participant_display_name(participant),
                )
                raise CombatServiceError(
                    f"Target {cls._participant_display_name(participant)} { _resolve_instance_spatial_error_phrase(result) }.",
                    400,
                )
            results_by_participant_id[participant["id"]] = result

        return results_by_participant_id

    @classmethod
    def _validate_instance_targets(cls, *, req, spell_context, state):
        raw = getattr(req, "effect_instance_targets", None)
        if not raw:
            if cls._normalize_lookup(spell_context.get("spell_canonical_key")) == "magic missile":
                raise CombatServiceError(
                    "Magic Missile requires effect_instance_targets for every missile instance.",
                    400,
                )
            return None

        instance_count = spell_context.get("effect_instance_count", 1)
        if instance_count <= 1:
            raise CombatServiceError(
                "effect_instance_targets is only supported for multi-instance spells.", 400
            )

        indices = set()
        for t in raw:
            idx = t.instance_index
            if idx < 1 or idx > instance_count:
                raise CombatServiceError(
                    f"Instance index {idx} is out of range (1..{instance_count}).", 400
                )
            if idx in indices:
                raise CombatServiceError(
                    f"Duplicate instance index: {idx}.", 400
                )
            indices.add(idx)

        missing = set(range(1, instance_count + 1)) - indices
        if missing:
            sorted_missing = sorted(missing)
            raise CombatServiceError(
                f"Missing instance target assignments: {', '.join(str(m) for m in sorted_missing)}.", 400
            )

        participants_by_ref = {p["ref_id"]: p for p in state.participants}
        validated = []
        for t in raw:
            participant = participants_by_ref.get(t.target_ref_id)
            if participant is None:
                raise CombatServiceError(
                    f"Invalid target_ref_id for instance {t.instance_index}: {t.target_ref_id}.", 400
                )
            validated.append({
                "instance_index": t.instance_index,
                "target_ref_id": t.target_ref_id,
                "participant": participant,
            })

        return validated

    @classmethod
    def _validate_instance_spatial_targets(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        validated_targets: list[dict],
        session_id: str,
    ) -> dict[str, TargetingResult]:
        """Validate range/LoS/LoE for each unique targetRefId before consuming any resources.

        Deduplicates validation by targetRefId — each unique target is validated once.
        Raises CombatServiceError with instance_index and reason on first failure.
        Returns a dict of TargetingResult keyed by target_ref_id so that cover metadata
        can be reused downstream (e.g. in _resolve_instance_attack) without re-validating.
        """
        targeting_service = get_combat_targeting_service(state.use_map)

        unique_ref_to_first_instance: dict[str, int] = {}
        for vt in validated_targets:
            ref_id = vt["target_ref_id"]
            if ref_id not in unique_ref_to_first_instance:
                unique_ref_to_first_instance[ref_id] = vt["instance_index"]

        results_by_ref: dict[str, TargetingResult] = {}

        for target_ref_id, first_instance_index in unique_ref_to_first_instance.items():
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-instance:{first_instance_index}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_ref_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                spell_mode=spell_context["spell_mode"],
                target_type=spell_context.get("target_type"),
                selection_type=spell_context.get("selection_type"),
                attack_type=spell_context.get("attack_type"),
                range_kind=spell_context.get("range_kind"),
                area_shape=spell_context.get("area_shape"),
                range_meters=spell_context.get("range_meters"),
                requires_sight=bool(spell_context.get("requires_target_sight")),
                requires_effect=bool(spell_context.get("requires_target_effect")),
            )
            result = targeting_service.validate(intent, state)

            if not result.is_valid:
                participant = next(
                    (vt["participant"] for vt in validated_targets if vt["target_ref_id"] == target_ref_id),
                    None,
                )
                target_label = (participant or {}).get("display_name") or target_ref_id
                reason = cls._map_spell_rejection_reason(
                    result.diagnostics.primary_failure() if result.diagnostics else None
                )
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=attacker.get("actor_user_id"),
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=reason,
                    target_ref_id=target_ref_id,
                    target_display_name=target_label,
                    instance_index=first_instance_index,
                )
                reason_phrase = _resolve_instance_spatial_error_phrase(result)
                raise CombatServiceError(
                    f"Instance {first_instance_index} target {target_label} {reason_phrase}.",
                    status_code=400,
                )

            results_by_ref[target_ref_id] = result

        return results_by_ref

    @classmethod
    def _resolve_instance_direct(cls, db, state, attacker, target_p, spell_context, req):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )
        effect_kind = spell_context.get("effect_kind") or "damage"
        damage_type = spell_context.get("damage_type")

        _, total = cls._resolve_damage_roll(instance_dice, roll_source="system")
        amount = max(0, total)

        new_hp = None
        previous_hp = None
        if amount > 0:
            new_hp, _, previous_hp, _ = cls._apply_spell_effect(
                db, state,
                target_p["ref_id"], target_p["kind"],
                effect_kind, amount,
                damage_type=damage_type,
                concentration_roll_source=req.concentration_roll_source,
                concentration_manual_roll=req.concentration_manual_roll,
                attacker_participant_id=attacker.get("id"),
            )

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": amount if effect_kind != "healing" else 0,
            "healing": amount if effect_kind == "healing" else 0,
            "is_hit": None,
            "is_saved": None,
            "is_critical": False,
            "roll": None,
            "roll_result": None,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
        }

    @classmethod
    def _resolve_instance_attack(
        cls, db, session_id, state, attacker, target_p, spell_context, req, is_gm,
        *,
        targeting_result: TargetingResult | None = None,
    ):
        instance_dice = spell_context.get("effect_instance_dice")
        if not instance_dice:
            raise CombatServiceError(
                "Multi-instance spell is missing effect_instance_dice.", 400
            )
        effect_kind = spell_context.get("effect_kind") or "damage"
        damage_type = spell_context.get("damage_type")
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)

        _, target_ac_raw, *_ = cls._get_stats(
            db,
            target_p["ref_id"],
            target_p["kind"],
            session_id,
            combat_state=state,
        )
        cover = targeting_result.spatial_metadata.cover if targeting_result else None
        cover_modifier = resolve_cover_modifier(cover)
        base_ac = target_ac_raw if target_ac_raw is not None else 10
        target_ac = base_ac + cover_modifier

        adv_ctx = resolve_attack_advantage(attacker, target_p, resolve_spell_attack_kind())
        has_adv = req.has_advantage or bool(adv_ctx.advantage_sources)
        has_dis = req.has_disadvantage or bool(adv_ctx.disadvantage_sources)
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
            target_ac=target_ac,
            roll_source="system",
        )
        roll_result.is_gm_roll = is_gm
        roll_result.roll_source = "system"

        is_critical = roll_result.selected_roll == 20
        is_hit = bool(roll_result.success)

        damage = 0
        healing = 0
        new_hp = None
        previous_hp = None

        if is_hit:
            _, total = cls._resolve_damage_roll(instance_dice, critical=is_critical, roll_source="system")
            amount = max(0, total)
            if amount > 0:
                new_hp, _, previous_hp, _ = cls._apply_spell_effect(
                    db, state,
                    target_p["ref_id"], target_p["kind"],
                    effect_kind, amount,
                    damage_type=damage_type,
                    is_critical=is_critical,
                    concentration_roll_source=req.concentration_roll_source,
                    concentration_manual_roll=req.concentration_manual_roll,
                    attacker_participant_id=attacker.get("id"),
                )
                if effect_kind == "healing":
                    healing = amount
                else:
                    damage = amount
        else:
            flag_modified(state, "participants")

        return {
            "target_ref_id": target_p["ref_id"],
            "target_display_name": target_p.get("display_name", ""),
            "target_kind": target_p.get("kind", "session_entity"),
            "damage": damage,
            "healing": healing,
            "is_hit": is_hit,
            "is_saved": None,
            "is_critical": is_critical,
            "roll": roll_result.total,
            "roll_result": roll_result,
            "new_hp": new_hp,
            "previous_hp": previous_hp,
            "cover": cover,
            "base_ac": base_ac,
            "effective_ac": target_ac,
            "cover_modifier": cover_modifier,
        }

    @classmethod
    async def _resolve_multi_instance_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm, validated_targets,
        *,
        spatial_results_by_target_ref: dict[str, TargetingResult] | None = None,
    ):
        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(inventory_item, source_item)
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)

        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker, action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        spell_mode = spell_context["spell_mode"]
        is_hostile = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        if is_hostile:
            seen = set()
            for vt in validated_targets:
                ref_id = vt["target_ref_id"]
                if ref_id not in seen:
                    cls._assert_hostile_action_allowed(
                        attacker, vt["participant"], action_label="a hostile spell",
                    )
                    seen.add(ref_id)

        logger.info(
            "[cast_spell] pipeline=multi_instance spell=%s instances=%d session=%s actor=%s",
            spell_context["spell_canonical_key"],
            len(validated_targets),
            session_id,
            attacker.get("ref_id"),
        )

        outcomes = []
        entity_previous_hp_map = {}

        for vt in validated_targets:
            target_p = vt["participant"]

            if spell_mode == "spell_attack":
                instance_targeting_result = (spatial_results_by_target_ref or {}).get(
                    vt["target_ref_id"]
                )
                outcome = cls._resolve_instance_attack(
                    db, session_id, state, attacker, target_p, spell_context, req, is_gm,
                    targeting_result=instance_targeting_result,
                )
            else:
                outcome = cls._resolve_instance_direct(
                    db, state, attacker, target_p, spell_context, req,
                )
                is_magic_missile = cls._normalize_lookup(spell_context.get("spell_canonical_key")) == "magic missile"
                if is_magic_missile and cls._is_shielded_for_magic_missile(target_p):
                    outcome["damage"] = 0
                    outcome["new_hp"] = None

            outcome["instance_index"] = vt["instance_index"]
            outcomes.append(outcome)

            ref_id = vt["target_ref_id"]
            if ref_id not in entity_previous_hp_map and outcome.get("previous_hp") is not None:
                entity_previous_hp_map[ref_id] = outcome["previous_hp"]

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        player_state_ids = set()
        if slot_spent:
            player_state_ids.add(attacker["ref_id"])

        for outcome in outcomes:
            if outcome["damage"] > 0 or outcome["healing"] > 0:
                if outcome["target_kind"] == "player":
                    player_state_ids.add(outcome["target_ref_id"])

        for player_ref_id in player_state_ids:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            target_p_entity = next(
                (p for p in state.participants if p["ref_id"] == ref_id), None,
            )
            if target_p_entity and target_p_entity.get("kind") == "session_entity":
                await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        log_message = cls._build_multi_instance_log_message(
            attacker=attacker,
            spell_context=spell_context,
            outcomes=outcomes,
            was_overridden=was_overridden,
            action_cost=action_cost,
        )
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        total_damage = sum(o["damage"] for o in outcomes)
        total_healing = sum(o["healing"] for o in outcomes)
        first_outcome = outcomes[0] if outcomes else None
        per_target_totals: dict[str, dict[str, object]] = {}
        for outcome in outcomes:
            target_ref_id = str(outcome.get("target_ref_id") or "")
            if not target_ref_id:
                continue
            bucket = per_target_totals.setdefault(
                target_ref_id,
                {
                    "target_ref_id": target_ref_id,
                    "target_display_name": outcome.get("target_display_name") or target_ref_id,
                    "target_kind": outcome.get("target_kind") or "session_entity",
                    "instance_count": 0,
                    "damage": 0,
                    "healing": 0,
                },
            )
            bucket["instance_count"] = cls._safe_int(bucket.get("instance_count"), 0) + 1
            bucket["damage"] = cls._safe_int(bucket.get("damage"), 0) + cls._safe_int(outcome.get("damage"), 0)
            bucket["healing"] = cls._safe_int(bucket.get("healing"), 0) + cls._safe_int(outcome.get("healing"), 0)

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_mode,
            "effect_kind": spell_context.get("effect_kind"),
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": first_outcome["target_display_name"] if first_outcome else "",
            "target_kind": first_outcome["target_kind"] if first_outcome else "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_instance_dice"),
            "effect_bonus": 0,
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "effect_rolls": [],
            "base_effect": None,
            "effect_roll_source": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": len(validated_targets),
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": outcomes,
            "effect_instance_target_totals": list(per_target_totals.values()),
        }

    @classmethod
    async def _resolve_modal_multi_target_cast(
        cls,
        db,
        session_id,
        req,
        state,
        attacker,
        attacker_model,
        spell_context,
        actor_user_id,
        is_gm,
        validated_assignments,
        *,
        spatial_results_by_participant_id: dict[str, TargetingResult] | None = None,
    ):
        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(inventory_item, source_item)
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)

        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        shared_effect_group_id = str(uuid4()) if spell_context.get("concentration") else None
        outcomes: list[dict] = []
        target_variant_assignments: list[dict] = []
        manual_notes_by_target: list[dict] = []
        player_state_ids_to_emit = set()
        entity_previous_hp_map: dict[str, int] = {}
        total_damage = 0
        total_healing = 0
        spell_mode = spell_context["spell_mode"]

        is_hostile_spell = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        for assignment in validated_assignments:
            if is_hostile_spell:
                cls._assert_hostile_action_allowed(
                    attacker,
                    assignment["participant"],
                    action_label="a hostile spell",
                )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=assignment["participant"],
            )
            cls._validate_spell_target_creature_type_restriction(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=assignment["participant"],
            )

        for assignment in validated_assignments:
            participant = assignment["participant"]
            variant = assignment["variant"]
            target_variant_assignments.append(
                {
                    "target_ref_id": participant.get("ref_id"),
                    "target_participant_id": participant.get("id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                }
            )
            if variant.manualNotes:
                manual_notes_by_target.append(
                    cls._build_variant_summary_for_target(
                        participant=participant,
                        variant=variant,
                    )
                )

            per_target_context = cls._merge_spell_context_with_variant(
                spell_context=spell_context,
                variant=variant,
                participant=participant,
                target_variant_assignments=target_variant_assignments,
            )
            automation_result = await cls._cast_spell_via_automation(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=per_target_context,
                target_participant=participant,
            )
            if automation_result is None:
                automation_result = await cls._cast_spell_via_declarative_effects(
                    db,
                    session_id,
                    attacker=attacker,
                    attacker_model=attacker_model,
                    actor_user_id=actor_user_id,
                    is_gm=is_gm,
                    req=req,
                    state=state,
                    spell_context=per_target_context,
                    target_participant=participant,
                    effect_group_id=shared_effect_group_id,
                )

            if automation_result is not None:
                if automation_result.get("pending_spell_id") or automation_result.get("pending_save_id"):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "target_kind": participant.get("kind", "session_entity"),
                    "damage": automation_result.get("damage", 0) or 0,
                    "healing": automation_result.get("healing", 0) or 0,
                    "is_hit": automation_result.get("is_hit"),
                    "is_saved": automation_result.get("is_saved"),
                    "is_critical": automation_result.get("is_critical", False),
                    "roll": automation_result.get("roll"),
                    "roll_result": automation_result.get("roll_result"),
                    "new_hp": automation_result.get("new_hp"),
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                    "summary_text": automation_result.get("summary_text"),
                }
                player_state_ids_to_emit.update(
                    automation_result.get("__player_state_ids_to_emit") or set()
                )
            elif spell_mode == "spell_attack":
                outcome = cls._resolve_instance_attack(
                    db,
                    session_id,
                    state,
                    attacker,
                    participant,
                    per_target_context,
                    req,
                    is_gm,
                    targeting_result=(spatial_results_by_participant_id or {}).get(participant["id"]),
                )
                outcome["variant_key"] = assignment["variant_key"]
                outcome["variant_label"] = assignment["variant_label"]
                if outcome.get("roll_result") and (
                    outcome.get("roll_result").pending_spell_id
                    or outcome.get("roll_result").pending_save_id
                ):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
            elif spell_mode == "saving_throw":
                resolution = cls._resolve_saving_throw_spell(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=per_target_context,
                    req=req,
                    is_gm=is_gm,
                    spell_mode=spell_mode,
                    effect_kind=per_target_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(per_target_context.get("effect_bonus"), 0),
                    effect_roll_required=per_target_context["effect_dice"] is not None,
                    save_success_outcome=per_target_context.get("save_success_outcome"),
                    targeting_result=(spatial_results_by_participant_id or {}).get(participant["id"]),
                )
                if resolution.pending_spell_id or resolution.pending_save_id:
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "target_kind": participant.get("kind", "session_entity"),
                    "damage": resolution.damage,
                    "healing": resolution.healing,
                    "is_hit": None,
                    "is_saved": resolution.is_saved,
                    "is_critical": False,
                    "roll": resolution.roll_total,
                    "roll_result": resolution.roll_result,
                    "new_hp": resolution.new_hp,
                    "variant_key": assignment["variant_key"],
                    "variant_label": assignment["variant_label"],
                }
            else:
                outcome = cls._resolve_direct_effect_spell(
                    db,
                    state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=per_target_context,
                    req=req,
                    spell_mode=spell_mode,
                    effect_kind=per_target_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(per_target_context.get("effect_bonus"), 0),
                    effect_roll_required=per_target_context["effect_dice"] is not None,
                ).__dict__
                if outcome.get("pending_spell_id") or outcome.get("pending_save_id"):
                    raise CombatServiceError(
                        "Multi-target modal spells do not support pending follow-up resolution yet.",
                        400,
                    )
                outcome["target_ref_id"] = participant.get("ref_id")
                outcome["target_display_name"] = cls._participant_display_name(participant)
                outcome["target_kind"] = participant.get("kind", "session_entity")
                outcome["variant_key"] = assignment["variant_key"]
                outcome["variant_label"] = assignment["variant_label"]

            outcomes.append(outcome)
            total_damage += outcome.get("damage", 0) or 0
            total_healing += outcome.get("healing", 0) or 0
            previous_hp = outcome.get("previous_hp")
            if previous_hp is not None and participant.get("ref_id") not in entity_previous_hp_map:
                entity_previous_hp_map[participant.get("ref_id")] = previous_hp
            if participant.get("kind") == "player" and (
                (outcome.get("damage", 0) or 0) > 0 or (outcome.get("healing", 0) or 0) > 0
            ):
                player_state_ids_to_emit.add(participant.get("ref_id"))

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            player_state_ids_to_emit.add(attacker["ref_id"])

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            target_p_entity = next(
                (p for p in state.participants if p["ref_id"] == ref_id), None,
            )
            if target_p_entity and target_p_entity.get("kind") == "session_entity":
                await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        target_count = len(validated_assignments)
        target_names = ", ".join(
            cls._participant_display_name(assignment["participant"])
            for assignment in validated_assignments
        )
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em {target_count} alvo"
            f"{'s' if target_count != 1 else ''}: {target_names}."
        )
        log_message = (
            f"{log_message}"
            f"{cls._format_variant_assignments_for_log(target_variant_assignments, manual_notes_by_target)}"
            f"{cls._format_manual_notes_for_log(manual_notes_by_target)}"
            f"{cls._format_concentration_group_for_log(shared_effect_group_id)}"
        ).strip()
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": None,
            "selected_variant_label": None,
            "context_origin": "initial_cast",
            "concentration_group": shared_effect_group_id,
            "action_kind": spell_mode,
            "effect_kind": spell_context.get("effect_kind"),
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": f"{target_count} alvos",
            "target_kind": "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": f"{spell_context['spell_name']} aplicou efeitos em {target_count} alvos.",
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": target_count,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
            "effect_instance_count": spell_context.get("effect_instance_count"),
            "effect_instance_dice": spell_context.get("effect_instance_dice"),
            "base_effect_instance_count": spell_context.get("base_effect_instance_count"),
            "effect_instance_outcomes": [],
            "target_variant_assignments": target_variant_assignments,
            "manual_notes_by_target": manual_notes_by_target,
        }

    @classmethod
    async def _resolve_cast_resolution(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm,
    ):
        targeting_intent = SpellCastIntent(
            session_id=session_id,
            action_id=f"targeting:{uuid4()}",
            actor_ref_id=attacker["ref_id"],
            actor_kind=attacker["kind"],
            requested_target_ref_id=req.target_ref_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            spell_mode=spell_context["spell_mode"],
            target_type=spell_context.get("target_type"),
            selection_type=spell_context.get("selection_type"),
            attack_type=spell_context.get("attack_type"),
            range_kind=spell_context.get("range_kind"),
            area_shape=spell_context.get("area_shape"),
            range_meters=spell_context.get("range_meters"),
            requires_sight=bool(spell_context.get("requires_target_sight")),
            requires_effect=bool(spell_context.get("requires_target_effect")),
        )
        targeting_result = get_combat_targeting_service(state.use_map).validate(
            targeting_intent, state
        )
        if not targeting_result.is_valid:
            diag = targeting_result.diagnostics
            logger.info(
                "[cast_spell] targeting failed session=%s actor=%s target=%s | %s",
                session_id,
                attacker.get("ref_id"),
                req.target_ref_id,
                diag.compact_log() if diag else targeting_result.failure_reason,
            )
            target_p = next(
                (p for p in state.participants if p["ref_id"] == req.target_ref_id),
                None,
            )
            cls._record_spell_cast_rejected_activity(
                db,
                session_id=session_id,
                actor_user_id=actor_user_id,
                actor_ref_id=attacker["ref_id"],
                actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                spell_context=spell_context,
                reason=cls._map_spell_rejection_reason(
                    diag.primary_failure() if diag else None
                ),
                target_ref_id=req.target_ref_id,
                target_display_name=target_p.get("display_name") if target_p else None,
            )
            raise CombatServiceError(
                targeting_result.failure_reason or "Target not found in combat"
            )

        target_p = next(
            (
                p
                for p in state.participants
                if p["ref_id"] == targeting_result.validated_primary_target_ref_id
            ),
            None,
        )
        if not target_p:
            raise CombatServiceError("Target not found in combat")

        is_hostile_spell = (
            spell_context["spell_mode"] in ("spell_attack", "saving_throw", "direct_damage")
            or spell_context["spell_canonical_key"] == "hunters_mark"
        )
        if is_hostile_spell:
            cls._assert_hostile_action_allowed(
                attacker,
                target_p,
                action_label="a hostile spell",
            )
        cls._validate_spell_automation_target(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        cls._validate_spell_target_creature_type_restriction(
            db,
            session_id,
            spell_canonical_key=spell_context["spell_canonical_key"],
            target_participant=target_p,
        )
        cls._check_declarative_requires_unarmored_for_target(
            db,
            session_id,
            spell_context=spell_context,
            target_participant=target_p,
        )

        slot_spent = False
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(
                inventory_item, source_item
            )
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )

        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        effect_roll_required = spell_context["effect_dice"] is not None
        spell_mode = spell_context["spell_mode"]
        effect_kind = spell_context["effect_kind"]
        effect_bonus = cls._safe_int(spell_context.get("effect_bonus"), 0)
        save_success_outcome = spell_context.get("save_success_outcome")
        inventory_refresh_required = spell_context.get("source_kind") == "magic_item"
        summary_text = None
        custom_log_message = None
        automation_player_state_ids = set()

        automation_result = await cls._cast_spell_via_automation(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_p,
        )
        # Spell attacks with declarative effects must go through the attack-roll
        # path first; applying effects before the roll would bypass hit/miss.
        if automation_result is None and spell_mode not in ("spell_attack", "saving_throw"):
            automation_result = await cls._cast_spell_via_declarative_effects(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=target_p,
            )
        on_hit_applied_declarative_effects_by_target: list | None = None
        if automation_result is not None:
            spell_mode = automation_result["action_kind"]
            effect_kind = automation_result["effect_kind"]
            result = SpellResolutionResult(
                roll_result=automation_result["roll_result"],
                roll_total=automation_result["roll"],
                target_ac=automation_result["target_ac"],
                is_critical=automation_result["is_critical"],
                is_hit=automation_result["is_hit"],
                is_saved=automation_result["is_saved"],
                new_hp=automation_result["new_hp"],
                pending_spell_id=automation_result["pending_spell_id"],
                damage=automation_result["damage"],
                healing=automation_result["healing"],
            )
            effect_roll_required = automation_result["effect_roll_required"]
            summary_text = automation_result.get("summary_text")
            inventory_refresh_required = inventory_refresh_required or bool(
                automation_result.get("inventory_refresh_required")
            )
            custom_log_message = automation_result.get("__log_message")
            automation_player_state_ids = automation_result.get("__player_state_ids_to_emit") or set()
        elif spell_mode == "spell_attack":
            result = cls._resolve_spell_attack(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                targeting_result=targeting_result,
            )
            # Apply declarative on-hit effects (e.g. Ray of Frost movement penalty).
            # Only applies when the attack lands and there is no pending dice roll.
            if result.is_hit and not result.pending_spell_id:
                if cls._spell_context_has_declarative_effects(spell_context):
                    application = cls._apply_declarative_spell_effects(
                        state=state,
                        attacker=attacker,
                        target_participant=target_p,
                        spell_context=spell_context,
                    )
                    applied_effects = application["applied_effects"]
                    cls._apply_temp_hp_from_granted_effects(db, state, applied_effects)
                    on_hit_applied_declarative_effects_by_target = (
                        cls._build_applied_declarative_effects_by_target(applied_effects)
                    )
        elif spell_mode == "saving_throw":
            result = cls._resolve_saving_throw_spell(
                db,
                session_id,
                state=state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                is_gm=is_gm,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
                save_success_outcome=save_success_outcome,
                targeting_result=targeting_result,
            )
            if (
                automation_result is None
                and result.is_saved is False
                and not result.pending_spell_id
                and not result.pending_save_id
                and cls._spell_context_has_declarative_effects(spell_context)
            ):
                application = cls._apply_declarative_spell_effects(
                    state=state,
                    attacker=attacker,
                    target_participant=target_p,
                    spell_context=spell_context,
                )
                for active_effect in application.get("applied_effects") or []:
                    metadata = cls._get_effect_metadata(active_effect)
                    repeat_save = metadata.get("repeat_save")
                    if isinstance(repeat_save, dict) and repeat_save.get("timing") == "target_turn_end":
                        repeat_save["dc"] = result.effective_dc
                        repeat_save["ability"] = str(spell_context.get("save_ability") or "wisdom")
                        repeat_save["source_participant_id"] = attacker.get("id")
                on_hit_applied_declarative_effects_by_target = (
                    cls._build_applied_declarative_effects_by_target(
                        application.get("applied_effects")
                    )
                )
        else:
            result = cls._resolve_direct_effect_spell(
                db,
                state,
                attacker=attacker,
                target_p=target_p,
                spell_context=spell_context,
                req=req,
                spell_mode=spell_mode,
                effect_kind=effect_kind,
                effect_bonus=effect_bonus,
                effect_roll_required=effect_roll_required,
            )

        return {
            "result": result,
            "spell_mode": spell_mode,
            "effect_kind": effect_kind,
            "effect_bonus": effect_bonus,
            "save_success_outcome": save_success_outcome,
            "slot_spent": slot_spent,
            "inventory_refresh_required": inventory_refresh_required,
            "summary_text": summary_text,
            "custom_log_message": custom_log_message,
            "automation_player_state_ids": automation_player_state_ids,
            "was_overridden": was_overridden,
            "action_cost": action_cost,
            "target_p": target_p,
            "automation_result": automation_result,
            "on_hit_applied_declarative_effects_by_target": on_hit_applied_declarative_effects_by_target,
        }

    @classmethod
    async def _resolve_no_external_target_cast(
        cls, db, session_id, req, state, attacker, attacker_model,
        spell_context, actor_user_id, is_gm,
    ):
        slot_spent = False
        is_shield = cls._normalize_lookup(spell_context.get("spell_canonical_key")) == "shield"
        shield_pending_attacker = None
        shield_pending_payload = None
        if is_shield:
            for participant in state.participants:
                pending = participant.get("pending_attack")
                if not isinstance(pending, dict):
                    continue
                if pending.get("target_ref_id") != attacker.get("ref_id"):
                    continue
                if pending.get("type") != "player_attack":
                    continue
                attack_roll = cls._safe_int(pending.get("roll"), 0)
                target_ac = cls._safe_int(pending.get("target_ac"), 10)
                if attack_roll < target_ac:
                    continue
                shield_pending_attacker = participant
                shield_pending_payload = pending
                break
            if shield_pending_payload is None:
                raise CombatServiceError("Shield requires an incoming hit trigger.", 400)
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            remaining_charges = get_inventory_item_charges_current(
                inventory_item, source_item
            )
            if isinstance(remaining_charges, int) and remaining_charges <= 0:
                raise CombatServiceError("This item has no charges remaining.", 400)
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        if spell_context.get("source_kind") == "magic_item":
            inventory_item = spell_context.get("inventory_item")
            source_item = spell_context.get("source_item")
            if not isinstance(inventory_item, InventoryItem):
                raise CombatServiceError("Magic item inventory entry is missing.", 400)
            try:
                consume_inventory_item_charge(inventory_item, source_item)
            except ValueError as exc:
                raise CombatServiceError(str(exc), 400) from exc
            db.add(inventory_item)
        elif isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True
        if is_shield:
            cls._upsert_shield_temp_ac_effect(
                attacker,
                source_participant_id=attacker.get("id"),
            )
            pending_roll = cls._safe_int(shield_pending_payload.get("roll"), 0)
            _, recalculated_ac, *_ = cls._get_stats(
                db,
                attacker["ref_id"],
                attacker["kind"],
                session_id,
                combat_state=state,
            )
            recalculated_ac = recalculated_ac or 10
            if pending_roll < recalculated_ac:
                cls._clear_participant_pending_attack(shield_pending_attacker)
                flag_modified(state, "participants")

        automation_result = await cls._cast_spell_via_automation(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=attacker,
        )
        if automation_result is None:
            automation_result = await cls._cast_spell_via_declarative_effects(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=attacker,
            )
        if automation_result is not None:
            result = SpellResolutionResult(
                roll_result=automation_result["roll_result"],
                roll_total=automation_result["roll"],
                target_ac=automation_result["target_ac"],
                is_critical=automation_result["is_critical"],
                is_hit=automation_result["is_hit"],
                is_saved=automation_result["is_saved"],
                new_hp=automation_result["new_hp"],
                pending_spell_id=automation_result["pending_spell_id"],
                damage=automation_result["damage"],
                healing=automation_result["healing"],
            )
            return await cls._commit_cast_result(
                db,
                session_id,
                state,
                attacker,
                spell_context,
                {
                    "result": result,
                    "spell_mode": automation_result["action_kind"],
                    "effect_kind": automation_result["effect_kind"],
                    "effect_bonus": cls._safe_int(
                        automation_result.get("effect_bonus"), 0
                    ),
                    "save_success_outcome": spell_context.get("save_success_outcome"),
                    "slot_spent": slot_spent,
                    "inventory_refresh_required": spell_context.get("source_kind") == "magic_item"
                    or bool(automation_result.get("inventory_refresh_required")),
                    "summary_text": automation_result.get("summary_text"),
                    "custom_log_message": automation_result.get("__log_message"),
                    "automation_player_state_ids": automation_result.get("__player_state_ids_to_emit") or set(),
                    "was_overridden": was_overridden,
                    "action_cost": action_cost,
                    "target_p": attacker,
                    "automation_result": automation_result,
                },
                actor_user_id,
                is_gm,
            )

        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            target_state, *_ = cls._get_stats(db, attacker["ref_id"], "player", session_id)
            await cls._emit_player_state_update(db, session_id, attacker["ref_id"], target_state)
        await cls._emit_state(session_id, state)
        log_message = f"{attacker['display_name']} conjurou {spell_context['spell_name']}."
        if spell_context.get("effect_timing") == "triggered":
            log_message = f"{log_message} Efeito preparado para gatilho."
        elif spell_context.get("effect_timing") == "persistent":
            log_message = f"{log_message} Efeito persistente iniciado."
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(db, session_id, actor_user_id, attacker.get("display_name"), {
            "message": log_message,
            "actorUserId": actor_user_id,
            "source": "gm_override" if is_gm else "player_turn",
            "is_override": was_overridden,
            "overridden_resource": action_cost if was_overridden else None,
        })

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": spell_context["spell_mode"],
            "effect_kind": spell_context["effect_kind"],
            "damage": 0,
            "healing": 0,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": attacker.get("display_name"),
            "target_kind": attacker.get("kind"),
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": None,
            "inventory_refresh_required": spell_context.get("source_kind") == "magic_item",
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": 0,
            "elemental_affinity_eligible": bool(spell_context.get("elemental_affinity_eligible")),
            "elemental_affinity_damage_type": spell_context.get("elemental_affinity_damage_type"),
            "elemental_affinity_bonus": spell_context.get("elemental_affinity_bonus"),
        }

    # ------------------------------------------------------------------
    # Plain multi-target automation cast (no variants, no effect instances)
    # ------------------------------------------------------------------

    @classmethod
    def _validate_plain_multi_target_refs(
        cls,
        *,
        req,
        spell_context: dict,
        state,
    ) -> list[dict] | None:
        """Return resolved participant list or None if not applicable.

        Raises CombatServiceError on invalid requests.
        """
        ref_ids = getattr(req, "target_ref_ids", None)
        if ref_ids is None:
            return None
        if len(ref_ids) == 0:
            raise CombatServiceError(
                "This cast requires at least 1 target.",
                400,
            )

        # Mutual exclusion with other targeting fields
        if (
            getattr(req, "target_ref_id", None)
            or getattr(req, "target_variant_assignments", None)
            or getattr(req, "effect_instance_targets", None)
        ):
            raise CombatServiceError(
                "target_ref_ids cannot be combined with target_ref_id, "
                "target_variant_assignments, or effect_instance_targets.",
                400,
            )

        # Spell must be configured for multi-target
        effective_max = spell_context.get("max_targets")
        if not isinstance(effective_max, int):
            raise CombatServiceError(
                "This spell is not configured for multi-target casting.", 400
            )

        # Duplicate check
        if len(ref_ids) != len(set(ref_ids)):
            raise CombatServiceError("Duplicate target IDs are not allowed.", 400)

        # Count check (against resolved effective_max_targets)
        if len(ref_ids) > effective_max:
            raise CombatServiceError(
                f"This cast allows at most {effective_max} target(s); "
                f"{len(ref_ids)} were provided.",
                400,
            )

        # Resolve each ref_id to a participant
        resolved: list[dict] = []
        for ref_id in ref_ids:
            participant = next(
                (p for p in state.participants if p.get("ref_id") == ref_id),
                None,
            )
            if participant is None:
                raise CombatServiceError(
                    f"Target '{ref_id}' not found in combat.", 400
                )
            resolved.append(participant)

        return resolved

    @classmethod
    def _validate_plain_multi_target_spatial(
        cls,
        *,
        db,
        state,
        attacker: dict,
        spell_context: dict,
        targets: list[dict],
        session_id: str,
    ) -> dict[str, "TargetingResult"]:
        """Fan out spatial validation (range, LoS, LoE) for each plain target.

        Runs before resource consumption.  Raises CombatServiceError if any
        target fails.  Mirrors _validate_modal_variant_spatial_targets.
        """
        targeting_service = get_combat_targeting_service(state.use_map)
        results: dict[str, "TargetingResult"] = {}

        for participant in targets:
            target_ref_id = participant.get("ref_id", "")
            intent = SpellCastIntent(
                session_id=session_id,
                action_id=f"targeting-plain:{participant.get('id')}",
                actor_ref_id=attacker["ref_id"],
                actor_kind=attacker["kind"],
                requested_target_ref_id=target_ref_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                spell_mode=spell_context["spell_mode"],
                target_type=spell_context.get("target_type"),
                selection_type=spell_context.get("selection_type"),
                attack_type=spell_context.get("attack_type"),
                range_kind=spell_context.get("range_kind"),
                area_shape=spell_context.get("area_shape"),
                range_meters=spell_context.get("range_meters"),
                requires_sight=bool(spell_context.get("requires_target_sight")),
                requires_effect=bool(spell_context.get("requires_target_effect")),
            )
            result = targeting_service.validate(intent, state)
            if not result.is_valid:
                diag = result.diagnostics
                cls._record_spell_cast_rejected_activity(
                    db,
                    session_id=session_id,
                    actor_user_id=attacker.get("actor_user_id"),
                    actor_ref_id=attacker["ref_id"],
                    actor_display_name=attacker.get("display_name") or attacker["ref_id"],
                    spell_context=spell_context,
                    reason=cls._map_spell_rejection_reason(
                        diag.primary_failure() if diag else None
                    ),
                    target_ref_id=target_ref_id,
                    target_display_name=cls._participant_display_name(participant),
                )
                raise CombatServiceError(
                    f"Target {cls._participant_display_name(participant)} "
                    f"{_resolve_instance_spatial_error_phrase(result)}.",
                    400,
                )
            results[participant["id"]] = result

        return results

    @classmethod
    async def _resolve_plain_multi_target_automation_cast(
        cls,
        db,
        session_id: str,
        req,
        state,
        attacker: dict,
        attacker_model,
        spell_context: dict,
        actor_user_id: str,
        is_gm: bool,
        targets: list[dict],
        *,
        spatial_results: dict | None = None,
    ) -> dict:
        """Consume resources once then invoke the automation handler per target.

        Modeled after _resolve_modal_multi_target_cast.  No variants.
        """
        from sqlalchemy.orm.attributes import flag_modified

        spell_mode = spell_context["spell_mode"]
        is_hostile_spell = spell_mode in ("spell_attack", "saving_throw", "direct_damage")
        player_state_ids_to_emit: set[str] = set()
        entity_previous_hp_map: dict[str, int] = {}
        total_damage = 0
        total_healing = 0
        outcomes: list[dict] = []
        shared_effect_group_id = str(uuid4()) if spell_context.get("concentration") else None
        any_effect_applied = False

        # Per-target mechanical validation (before resolving any)
        for participant in targets:
            if is_hostile_spell:
                cls._assert_hostile_action_allowed(
                    attacker, participant, action_label="a hostile spell"
                )
            cls._validate_spell_automation_target(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=participant,
            )
            cls._validate_spell_target_creature_type_restriction(
                db,
                session_id,
                spell_canonical_key=spell_context["spell_canonical_key"],
                target_participant=participant,
            )

        slot_spent = False
        action_cost = spell_context.get("action_cost") or "action"
        was_overridden = cls._consume_turn_resource(
            attacker,
            action_cost,
            is_gm=is_gm,
            override_resource_limit=req.override_resource_limit,
        )
        if isinstance(spell_context.get("slot_level"), int):
            cls._consume_player_spell_slot(attacker_model, spell_context["slot_level"])
            db.add(attacker_model)
            slot_spent = True

        # Per-target automation resolution
        for participant in targets:
            outcome = await cls._cast_spell_via_automation(
                db,
                session_id,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                req=req,
                state=state,
                spell_context=spell_context,
                target_participant=participant,
            )
            if outcome is None and spell_mode == "saving_throw":
                resolution = cls._resolve_saving_throw_spell(
                    db,
                    session_id,
                    state=state,
                    attacker=attacker,
                    target_p=participant,
                    spell_context=spell_context,
                    req=req,
                    is_gm=is_gm,
                    spell_mode=spell_mode,
                    effect_kind=spell_context.get("effect_kind"),
                    effect_bonus=cls._safe_int(spell_context.get("effect_bonus"), 0),
                    effect_roll_required=spell_context["effect_dice"] is not None,
                    save_success_outcome=spell_context.get("save_success_outcome"),
                    targeting_result=(spatial_results or {}).get(participant["id"]),
                )
                if (
                    resolution.is_saved is False
                    and not resolution.pending_spell_id
                    and not resolution.pending_save_id
                    and cls._spell_context_has_declarative_effects(spell_context)
                ):
                    application = cls._apply_declarative_spell_effects(
                        state=state,
                        attacker=attacker,
                        target_participant=participant,
                        spell_context=spell_context,
                        effect_group_id=shared_effect_group_id,
                    )
                    applied_effects = application.get("applied_effects") or []
                    if applied_effects:
                        any_effect_applied = True
                    for active_effect in applied_effects:
                        metadata = cls._get_effect_metadata(active_effect)
                        repeat_save = metadata.get("repeat_save")
                        if isinstance(repeat_save, dict) and repeat_save.get("timing") == "target_turn_end":
                            repeat_save["dc"] = resolution.effective_dc
                            repeat_save["ability"] = str(spell_context.get("save_ability") or "wisdom")
                            repeat_save["source_participant_id"] = attacker.get("id")
                    applied_by_target = cls._build_applied_declarative_effects_by_target(applied_effects)
                else:
                    applied_by_target = []
                outcome = {
                    "target_ref_id": participant.get("ref_id"),
                    "target_participant_id": participant.get("id"),
                    "target_display_name": cls._participant_display_name(participant),
                    "target_kind": participant.get("kind", "session_entity"),
                    "damage": resolution.damage,
                    "healing": resolution.healing,
                    "is_hit": None,
                    "is_saved": resolution.is_saved,
                    "is_critical": False,
                    "roll": resolution.roll_total,
                    "roll_result": resolution.roll_result,
                    "new_hp": resolution.new_hp,
                    "save": {
                        "ability": spell_context.get("save_ability"),
                        "dc": resolution.effective_dc,
                        "is_saved": resolution.is_saved,
                        "roll": resolution.roll_total,
                    },
                    "applied_declarative_effects_by_target": applied_by_target,
                }
            if outcome is None and spell_mode not in ("spell_attack", "saving_throw"):
                outcome = await cls._cast_spell_via_declarative_effects(
                    db,
                    session_id,
                    attacker=attacker,
                    attacker_model=attacker_model,
                    actor_user_id=actor_user_id,
                    is_gm=is_gm,
                    req=req,
                    state=state,
                    spell_context=spell_context,
                    target_participant=participant,
                    effect_group_id=shared_effect_group_id,
                )
            if outcome:
                if outcome.get("__applied_effect_count", 0):
                    any_effect_applied = True
                outcomes.append(outcome)
                total_damage += cls._safe_int(outcome.get("damage"), 0)
                total_healing += cls._safe_int(outcome.get("healing"), 0)
                if participant.get("kind") == "player":
                    player_state_ids_to_emit.add(participant["ref_id"])
                elif participant.get("kind") == "session_entity":
                    prev = outcome.get("previous_hp")
                    new = outcome.get("new_hp")
                    if isinstance(prev, int) and isinstance(new, int) and prev != new:
                        entity_previous_hp_map[participant["ref_id"]] = prev

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        if slot_spent:
            player_state_ids_to_emit.add(attacker["ref_id"])

        for player_ref_id in player_state_ids_to_emit:
            target_state, *_ = cls._get_stats(db, player_ref_id, "player", session_id)
            await cls._emit_player_state_update(db, session_id, player_ref_id, target_state)

        for ref_id, prev_hp in entity_previous_hp_map.items():
            await cls._emit_entity_hp_update(db, session_id, ref_id, prev_hp)

        await cls._emit_state(session_id, state)

        target_count = len(targets)
        target_names = ", ".join(cls._participant_display_name(p) for p in targets)
        log_message = (
            f"{attacker['display_name']} conjurou {spell_context['spell_name']} em "
            f"{target_count} alvo{'s' if target_count != 1 else ''}: {target_names}."
        )
        if was_overridden:
            log_message = f"[OVERRIDE: Limit for '{action_cost}' ignored] {log_message}"
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker.get("display_name"),
            {
                "message": log_message,
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
                "is_override": was_overridden,
                "overridden_resource": action_cost if was_overridden else None,
            },
        )

        return {
            "spell_name": spell_context["spell_name"],
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": None,
            "selected_variant_label": None,
            "context_origin": "initial_cast",
            "concentration_group": shared_effect_group_id if any_effect_applied else None,
            "action_kind": spell_mode,
            "effect_kind": spell_context.get("effect_kind"),
            "damage": total_damage,
            "healing": total_healing,
            "damage_type": spell_context.get("damage_type"),
            "is_critical": None,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": f"{target_count} alvos",
            "target_kind": "session_entity",
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": spell_context.get("effect_dice"),
            "effect_bonus": cls._safe_int(spell_context.get("effect_bonus"), 0),
            "pending_spell_id": None,
            "pending_save_id": None,
            "effect_roll_required": False,
            "base_effect": None,
            "action_cost": action_cost,
            "summary_text": (
                f"{spell_context['spell_name']} resolvido em {target_count} "
                f"alvo{'s' if target_count != 1 else ''}."
            ),
            "inventory_refresh_required": False,
            "concentration_check": None,
            "concentration_checks": [],
            "area_shape": None,
            "affected_target_ref_ids": [p.get("ref_id") for p in targets],
            "affected_cells": [],
            "area_target_outcomes": [],
            "target_count": target_count,
            "plain_multi_target_outcomes": outcomes,
        }

    @classmethod
    async def cast_spell(
        cls,
        db,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool,
    ):
        state, attacker, attacker_model = cls._validate_cast_prerequisites(
            db, session_id, req, actor_user_id, is_gm,
        )
        spell_context = cls._resolve_player_spell_context(
            db, session_id, attacker, attacker_model, req,
        )
        validated_variant_assignments = cls._validate_modal_target_variant_assignments(
            req=req,
            spell_context=spell_context,
            state=state,
        )
        if validated_variant_assignments:
            spatial_results_by_participant_id = cls._validate_modal_variant_spatial_targets(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                assignments=validated_variant_assignments,
                session_id=session_id,
            )
            return await cls._resolve_modal_multi_target_cast(
                db,
                session_id,
                req,
                state,
                attacker,
                attacker_model,
                spell_context,
                actor_user_id,
                is_gm,
                validated_variant_assignments,
                spatial_results_by_participant_id=spatial_results_by_participant_id,
            )
        validated_plain_targets = cls._validate_plain_multi_target_refs(
            req=req,
            spell_context=spell_context,
            state=state,
        )
        if validated_plain_targets is not None:
            plain_spatial_results = cls._validate_plain_multi_target_spatial(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                targets=validated_plain_targets,
                session_id=session_id,
            )
            return await cls._resolve_plain_multi_target_automation_cast(
                db,
                session_id,
                req,
                state,
                attacker,
                attacker_model,
                spell_context,
                actor_user_id,
                is_gm,
                validated_plain_targets,
                spatial_results=plain_spatial_results,
            )
        variant_map = cls._get_spell_variants_map(spell_context)
        if variant_map:
            selected_variant_key = spell_context.get("selected_variant_key")
            selected_variant = variant_map.get(selected_variant_key)
            if selected_variant is None:
                raise CombatServiceError(
                    "This spell requires choosing a variant before casting.",
                    400,
                )
            selected_participant = next(
                (
                    participant
                    for participant in state.participants
                    if participant.get("ref_id") == getattr(req, "target_ref_id", None)
                ),
                attacker if spell_context.get("selection_type") in ("self", "none") else None,
            )
            single_target_assignment = (
                [
                    {
                        "target_participant_id": selected_participant.get("id"),
                        "target_display_name": cls._participant_display_name(selected_participant),
                        "variant_key": selected_variant.key,
                        "variant_label": selected_variant.labelPt or selected_variant.labelEn or selected_variant.key,
                        "target_ref_id": selected_participant.get("ref_id"),
                    }
                ]
                if isinstance(selected_participant, dict)
                else None
            )
            spell_context = cls._merge_spell_context_with_variant(
                spell_context=spell_context,
                variant=selected_variant,
                participant=selected_participant,
                target_variant_assignments=single_target_assignment,
            )
        validated_targets = cls._validate_instance_targets(
            req=req, spell_context=spell_context, state=state,
        )
        if validated_targets is not None:
            spatial_results_by_target_ref = cls._validate_instance_spatial_targets(
                db=db,
                state=state,
                attacker=attacker,
                spell_context=spell_context,
                validated_targets=validated_targets,
                session_id=session_id,
            )
            return await cls._resolve_multi_instance_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm, validated_targets,
                spatial_results_by_target_ref=spatial_results_by_target_ref,
            )
        area_spell_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if cls._normalize_area_shape(spell_context.get("area_shape")) is not None:
            if area_spell_spec is None:
                raise CombatServiceError(
                    "This area spell is not configured for map targeting yet.", 400,
                )
            logger.info(
                "[cast_spell] pipeline=generic_area spell=%s session=%s actor=%s",
                spell_context["spell_canonical_key"],
                session_id,
                attacker.get("ref_id"),
            )
            return await cls._cast_area_spell(
                db, session_id, req,
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id=actor_user_id,
                is_gm=is_gm,
                state=state,
                spell_context=spell_context,
                area_spec=area_spell_spec,
            )

        if spell_context.get("spell_mode") == "teleport":
            return await cls._resolve_teleport_spell(
                db, session_id, req, state, attacker, attacker_model, spell_context, actor_user_id, is_gm
            )

        if spell_context.get("selection_type") in ("none", "self"):
            return await cls._resolve_no_external_target_cast(
                db, session_id, req, state, attacker, attacker_model,
                spell_context, actor_user_id, is_gm,
            )

        resolution = await cls._resolve_cast_resolution(
            db, session_id, req, state, attacker, attacker_model,
            spell_context, actor_user_id, is_gm,
        )
        return await cls._commit_cast_result(
            db, session_id, state, attacker, spell_context,
            resolution, actor_user_id, is_gm,
        )
