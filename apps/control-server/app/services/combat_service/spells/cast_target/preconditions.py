from __future__ import annotations

from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession
from app.services.spell_material_components import SpellMaterialError, validate_spell_material

from ...exceptions import CombatServiceError


class CastTargetPreconditionsMixin:
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
            "requires_target_hearing": spell_context.get("requires_target_hearing"),
            "save_ability": spell_context.get("save_ability"),
            "attack_miss_outcome": spell_context.get("attack_miss_outcome"),
            "damage_type": spell_context.get("damage_type"),
            "damage_preview": spell_context.get("effect_dice"),
            "delayed_damage_preview": spell_context.get("delayed_damage_preview"),
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
            "utility": spell_context.get("utility"),
            "materialComponent": spell_context.get("materialComponent"),
            "throw_attack": spell_context.get("throw_attack"),
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

