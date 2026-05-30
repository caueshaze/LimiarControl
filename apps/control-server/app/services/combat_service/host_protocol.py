from __future__ import annotations

from typing import Any, Literal, Protocol

from sqlmodel import Session

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.schemas.combat import CombatMapSelection
from app.schemas.roll import RollActorStats


class CombatServiceHostProtocol(Protocol):
    _ENTITY_ABILITY_ALIASES: dict[str, str] | set[str]
    _DEFAULT_TURN_RESOURCES: dict[str, Any]
    _INITIATIVE_SKIPPED_STATUSES: set[str]
    _DEMO_MAP_SELECTION: CombatMapSelection

    @classmethod
    def _as_dict(cls, value: object) -> dict[str, Any]: ...

    @classmethod
    def _safe_int(cls, value: object, default: int = 0) -> int: ...

    @classmethod
    def _safe_optional_int(cls, value: object) -> int | None: ...

    @classmethod
    def _ability_modifier(cls, score: int) -> int: ...

    @classmethod
    def _normalize_ability_name(cls, value: object) -> str | None: ...

    @classmethod
    def _normalize_damage_type(cls, value: object) -> str | None: ...

    @classmethod
    def _normalize_lookup(cls, value: object) -> str: ...

    @classmethod
    def _normalize_spell_variants(cls, raw_variants: object) -> list[Any]: ...

    @classmethod
    def _get_entity_spellcasting(
        cls, npc: CampaignEntity, overrides: dict[str, Any]
    ) -> dict[str, Any]: ...

    @classmethod
    def _get_entity_ability_score(
        cls, stats: dict[str, Any], overrides: dict[str, Any], ability_name: str
    ) -> int: ...

    @classmethod
    def _get_entity_armor_class(
        cls, npc: CampaignEntity, overrides: dict[str, Any]
    ) -> int: ...

    @classmethod
    def _get_entity_skill_overrides(
        cls, npc: CampaignEntity, overrides: dict[str, Any]
    ) -> dict[str, Any]: ...

    @classmethod
    def _get_entity_saving_throw_overrides(
        cls, npc: CampaignEntity, overrides: dict[str, Any]
    ) -> dict[str, Any]: ...

    @classmethod
    def _get_player_ability_score(cls, data: dict[str, Any], ability_name: str) -> int: ...

    @classmethod
    def _get_player_fighting_style(cls, data: dict[str, Any]) -> str | None: ...

    @classmethod
    def _get_session_entry(cls, db: Session, session_id: str) -> Any: ...

    @classmethod
    def _get_campaign_system_for_session(cls, db: Session, session_id: str) -> Any: ...

    @classmethod
    def _get_campaign_item_for_session(
        cls, db: Session, session_id: str, item_key: str
    ) -> Any: ...

    @classmethod
    def _get_spell_catalog_entry_for_session(
        cls, db: Session, session_id: str, canonical_key: str
    ) -> Any: ...

    @classmethod
    def _get_participant_by_ref(
        cls, state: CombatState | None, ref_id: str | None
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _get_current_participant(cls, state: CombatState) -> dict[str, Any]: ...

    @classmethod
    def get_state(cls, db: Session, session_id: str) -> CombatState | None: ...

    @classmethod
    def _mark_active_combat_time_started(
        cls, db: Session, session_id: str, state: CombatState
    ) -> None: ...

    @classmethod
    def _get_stats(
        cls, db: Session, ref_id: str, kind: str, session_id: str = "", *, combat_state: Any = None
    ) -> tuple[Any, Any, Any, Any, Any, Any]: ...

    @classmethod
    def _get_effect_metadata(cls, effect: dict[str, Any] | None) -> dict[str, Any]: ...

    @classmethod
    def _append_effect_to_participant(
        cls, participant: dict[str, Any], effect: dict[str, Any]
    ) -> None: ...

    @classmethod
    def _get_participant_effects(
        cls, participant: dict[str, Any]
    ) -> list[dict[str, Any]]: ...

    @classmethod
    def _set_participant_effects(
        cls, participant: dict[str, Any], effects: list[dict[str, Any]]
    ) -> None: ...

    @classmethod
    def _execute_on_end_effects_for_removed(
        cls,
        *,
        state: CombatState,
        removed_effects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...

    @classmethod
    def _cleanup_recurring_temp_hp_effects(
        cls,
        db: Session,
        state: CombatState,
        removed_effects: list[dict[str, Any]],
    ) -> None: ...

    @classmethod
    def _effect_label(cls, effect: dict[str, Any]) -> str: ...

    @classmethod
    def _get_turn_resources(cls, participant: dict[str, Any]) -> dict[str, Any]: ...

    @classmethod
    def _get_hunters_mark_effect_for_target(
        cls,
        participant: dict[str, Any],
        *,
        target_participant_id: str,
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _player_has_colossus_slayer(cls, data: dict[str, Any] | None) -> bool: ...

    @classmethod
    def _get_target_hp_snapshot(
        cls,
        db: Session,
        session_id: str,
        target_ref_id: str,
        target_kind: str,
    ) -> tuple[int | None, int | None]: ...

    @classmethod
    def _build_player_attack_context(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        data: dict[str, Any],
        requested_weapon_item_id: str | None = None,
        attacker_effects: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _resolve_player_weapon_item(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        weapon_item_id: str,
    ) -> tuple[Any, Any]: ...

    @classmethod
    def _resolve_player_inventory_spell_item(
        cls,
        db: Session,
        session_id: str,
        *,
        player_user_id: str,
        inventory_item_id: str,
    ) -> tuple[Any, Any, dict[str, Any]]: ...

    @classmethod
    def _resolve_player_spell_entry(
        cls,
        data: dict[str, Any],
        *,
        spell_canonical_key: str | None,
        spell_name: str | None = None,
        campaign_spell_id: str | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _resolve_shillelagh_weapon(
        cls,
        db: Session,
        session_id: str,
        *,
        player_user_id: str,
        requested_weapon_item_id: str | None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _build_combat_spell_effect_context(
        cls,
        *,
        spell_key: str,
        spell_name: str,
        caster_participant_id: str,
        target_participant_id: str,
        game_time_seconds: int,
        duration_seconds: int,
        concentration: bool,
        concentration_group: str | None,
        extra_metadata: dict[str, Any] | None = None,
        spell_save_dc: int | None = None,
    ) -> Any: ...

    @classmethod
    def _apply_factory_spell_effect_to_target(
        cls,
        *,
        state: CombatState,
        target_participant: dict[str, Any],
        effect: dict[str, Any],
        source_spell_key: str,
        replace_existing: bool = True,
    ) -> None: ...

    @classmethod
    def _build_roll_actor_stats_for_save(
        cls, db: Session, session_id: str, ref_id: str, kind: str, display_name: str
    ) -> RollActorStats: ...

    @classmethod
    def resolve_effective_creature_type(
        cls, db: Session, session_id: str, participant: dict[str, Any]
    ) -> str | None: ...

    @classmethod
    def normalize_creature_type(cls, value: object) -> str | None: ...

    @classmethod
    def resolve_player_effective_creature_type_from_state_json(
        cls, state_json: dict[str, Any] | None
    ) -> str: ...

    @classmethod
    def _find_participant_by_id(
        cls, state: CombatState | None, participant_id: str | None
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _find_participant_by_ref_id(
        cls, state: CombatState | None, ref_id: str | None
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _build_active_effect(
        cls,
        *,
        kind: str,
        source_participant_id: str | None,
        condition_type: str | None = None,
        numeric_value: int | None = None,
        duration_type: str = "manual",
        remaining_rounds: int | None = None,
        expires_at_participant_id: str | None = None,
        created_at_game_time_seconds: int | None = None,
        expires_at_game_time_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
        display_label: str | None = None,
    ) -> dict[str, Any]: ...

    @staticmethod
    def _base_spell_result(
        *,
        spell_name: str,
        spell_context: dict[str, Any],
        target_display_name: str,
        target_kind: str,
        action_kind: str = "utility",
        summary_text: str = "",
        log_message: str = "",
        inventory_refresh_required: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _apply_healing_to_target(
        cls,
        db: Session,
        target_ref_id: str,
        kind: str,
        amount: int,
        state: CombatState | None = None,
    ) -> tuple[int, str, int | None]: ...

    @classmethod
    def _require_active(cls, state: CombatState | None) -> None: ...

    @classmethod
    def _resolve_actor_participant(
        cls,
        state: CombatState,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _require_actor_status(
        cls, attacker: dict[str, Any], allowed_statuses: tuple[str, ...], message: str
    ) -> None: ...

    @classmethod
    def _require_action_capable(cls, actor: dict[str, Any]) -> None: ...

    @classmethod
    def _require_movement_capable(cls, actor: dict[str, Any]) -> None: ...

    @classmethod
    def calculate_player_armor_class_from_state(
        cls, data: dict[str, Any], *, active_effects: list[dict[str, Any]] | None = None
    ) -> int: ...

    @classmethod
    def _get_session_entity_and_campaign_entity(
        cls, db: Session, session_entity_id: str
    ) -> tuple[Any, CampaignEntity]: ...

    @classmethod
    def _assert_hostile_action_allowed(
        cls, actor: dict[str, Any], target: dict[str, Any], *, action_label: str
    ) -> None: ...

    @classmethod
    def _resolve_required_hostile_target(
        cls,
        state: CombatState,
        actor: dict[str, Any],
        target_participant_id: str | None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _resolve_skill_check_advantage_mode_for_actor(cls, *args: Any, **kwargs: Any) -> str: ...

    @classmethod
    def _build_npc_targeting_intent(
        cls,
        session_id: str,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        action_kind: str,
        resolved_action: dict[str, Any],
    ) -> Any: ...

    @classmethod
    def _clear_participant_pending_attack(cls, participant: dict[str, Any]) -> None: ...

    @classmethod
    def _sum_numeric_effects(
        cls, participant: dict[str, Any], kind: str
    ) -> int: ...

    @classmethod
    def _has_effect_kind(
        cls, participant: dict[str, Any], kind: str
    ) -> bool: ...

    @classmethod
    def _consume_first_effect(
        cls, participant: dict[str, Any], kind: str
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _consume_effect_ids(
        cls, participant: dict[str, Any], effect_ids: list[str]
    ) -> list[dict[str, Any]]: ...

    @classmethod
    def _create_pending_attack(
        cls,
        state: CombatState,
        participant: dict[str, Any],
        payload: dict[str, Any],
    ) -> str: ...

    @classmethod
    def _normalize_save_success_outcome(cls, value: object) -> str | None: ...

    @classmethod
    def _normalize_attack_miss_outcome(cls, value: object) -> str | None: ...

    @classmethod
    def _get_structured_spell_upcast(cls, raw_upcast: object) -> dict[str, Any] | None: ...

    @classmethod
    def _get_structured_cantrip_scaling(cls, raw_scaling: object) -> dict[str, Any] | None: ...

    @classmethod
    def _apply_structured_spell_upcast(
        cls,
        *,
        spell_level: int,
        slot_level: int | None,
        effect_kind: str | None,
        effect_dice: str | None,
        effect_bonus: int,
        upcast: dict[str, Any] | None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _apply_character_level_cantrip_scaling(
        cls,
        *,
        spell_level: int,
        caster_level: int | None,
        effect_dice: str | None,
        cantrip_scaling: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _build_dice_expression(
        cls,
        *,
        dice_count: int,
        dice_size: int,
        bonus: int = 0,
    ) -> str: ...

    @classmethod
    def _merge_dice_expressions(
        cls,
        base_expression: str | None,
        extra_expression: str | None,
        repeats: int = 1,
    ) -> str | None: ...

    @classmethod
    def _map_resolution_type_to_spell_mode(cls, resolution_type: object) -> str | None: ...

    @classmethod
    def _spell_default_mode_override(cls, canonical_key: object) -> str | None: ...

    @classmethod
    def _spell_requires_effect_payload(cls, canonical_key: object) -> bool: ...

    @classmethod
    def _resolve_spell_action_cost(cls, casting_time_type: object) -> str: ...

    @classmethod
    def _resolve_damage_roll(
        cls,
        damage_dice: str,
        *,
        critical: bool = False,
        roll_source: str = "system",
        manual_rolls: list[int] | None = None,
    ) -> tuple[list[int], int]: ...

    @classmethod
    def _resolve_save_damage_amount(
        cls,
        rolled_amount: int,
        *,
        is_saved: bool,
        save_success_outcome: str | None,
    ) -> int: ...

    @classmethod
    def _apply_damage_to_target(
        cls,
        db: Session,
        target_ref_id: str,
        kind: str,
        amount: int,
        is_crit: bool = False,
        state: CombatState | None = None,
        *,
        damage_type: str | None = None,
        is_magical_damage: bool = False,
        concentration_roll_source: str = "system",
        concentration_manual_roll: int | None = None,
        attacker_participant_id: str | None = None,
    ) -> tuple[int, str, int | None, Any]: ...

    @classmethod
    def _apply_roll_bonus_dice_to_roll_result(
        cls,
        *,
        participant: dict[str, Any],
        roll_result: Any,
        roll_type: Literal["attack", "save", "ability", "skill"],
        state: CombatState | None = None,
    ) -> list[str]: ...

    @classmethod
    def _build_pending_spell_context_from_payload(
        cls,
        pending_payload: dict[str, Any],
        *,
        target_participant: dict[str, Any] | None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _create_pending_spell_effect(
        cls, state: CombatState, participant: dict[str, Any], payload: dict[str, Any]
    ) -> str: ...

    @classmethod
    def _require_pending_spell_effect(
        cls,
        participant: dict[str, Any],
        pending_spell_id: str,
    ) -> dict[str, Any]: ...

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
        attacker_participant_id: str | None = None,
    ) -> tuple[int | None, str, int | None, dict[str, Any] | None]: ...

    @classmethod
    async def _cast_area_spell_effect(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        *,
        attacker: dict[str, Any],
        pending_spell: dict[str, Any],
        effect_kind: str,
        effect_dice: Any,
        effect_bonus: int,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _emit_entity_hp_update(
        cls,
        db: Session,
        session_id: str,
        session_entity_id: str,
        previous_hp: int | None,
    ) -> None: ...

    @classmethod
    async def _emit_player_state_update(
        cls,
        db: Session,
        session_id: str,
        player_user_id: str,
        state_model: Any,
    ) -> None: ...

    @classmethod
    async def _emit_state(cls, session_id: str, state: CombatState) -> None: ...

    @classmethod
    def _format_variant_assignments_for_log(
        cls,
        target_variant_assignments: object,
        manual_notes_by_target: object = None,
    ) -> str: ...

    @classmethod
    def _format_manual_notes_for_log(cls, manual_notes_by_target: object) -> str: ...

    @classmethod
    def _format_concentration_group_for_log(cls, concentration_group: object) -> str: ...

    @classmethod
    async def _emit_and_persist_log(
        cls,
        db: Session,
        session_id: str,
        actor_user_id: str | None,
        actor_name: str | None,
        log_payload: dict[str, Any],
    ) -> None: ...

    @classmethod
    def _build_cast_log_message(
        cls,
        *,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        spell_mode: str,
        effect_kind: str | None,
        result: Any,
        save_success_outcome: str | None,
        was_overridden: bool,
        action_cost: str,
        custom_log_message: str | None = None,
    ) -> str: ...

    @classmethod
    def _build_cast_response(
        cls,
        *,
        spell_context: dict[str, Any],
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        save_success_outcome: str | None,
        result: Any,
        automation_result: dict[str, Any] | None,
        target_p: dict[str, Any],
        action_cost: str,
        summary_text: str | None,
        inventory_refresh_required: bool,
        was_overridden: bool,
        on_hit_applied_declarative_effects_by_target: Any = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _sync_participant_status(
        cls,
        db: Session,
        state: CombatState | None,
        target_ref_id: str,
        kind: str,
        target_model: Any,
    ) -> str: ...

    @classmethod
    def _resolve_concentration_check_after_damage(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState | None,
        target_participant: dict[str, Any] | None,
        target_ref_id: str,
        target_kind: str,
        damage_taken: int,
        roll_source: str = "system",
        manual_roll: int | None = None,
    ) -> dict[str, Any] | None: ...

    @classmethod
    async def next_turn(
        cls,
        db: Session,
        session_id: str,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
        skip_turn_end_validation: bool = False,
    ) -> CombatState | None: ...

    @classmethod
    def _validate_spell_automation_target(
        cls,
        db: Session,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict[str, Any],
    ) -> None: ...

    @classmethod
    def _validate_spell_target_creature_type_restriction(
        cls,
        db: Session,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict[str, Any],
    ) -> None: ...

    @classmethod
    def _check_declarative_requires_unarmored_for_target(
        cls,
        db: Session,
        session_id: str,
        *,
        spell_context: dict[str, Any],
        target_participant: dict[str, Any],
    ) -> None: ...

    @classmethod
    def _validate_feather_fall_trigger_context(
        cls,
        *,
        req: Any,
        spell_context: dict[str, Any],
        targets: list[dict[str, Any]],
    ) -> None: ...

    @classmethod
    def _ensure_turn_resource_available(
        cls,
        participant: dict[str, Any],
        resource: str,
        *,
        is_gm: bool,
        override_resource_limit: bool = False,
    ) -> None: ...

    @classmethod
    def _ensure_player_spell_slot_available(
        cls,
        attacker_model: Any,
        slot_level: int,
    ) -> None: ...

    @classmethod
    def _participant_display_name(cls, participant: dict[str, Any] | None) -> str: ...

    @classmethod
    def _map_spell_rejection_reason(cls, reason: str | None) -> str: ...

    @classmethod
    def _record_spell_cast_rejected_activity(
        cls,
        db: Session,
        *,
        session_id: str,
        actor_user_id: str,
        actor_ref_id: str,
        actor_display_name: str,
        spell_context: dict[str, Any],
        reason: str,
        target_ref_id: str | None = None,
        target_display_name: str | None = None,
        instance_index: int | None = None,
        area_origin: dict[str, Any] | None = None,
    ) -> None: ...

    @classmethod
    def _build_variant_summary_for_target(
        cls,
        *,
        participant: dict[str, Any],
        variant: Any,
    ) -> dict[str, Any]: ...

    @classmethod
    def _merge_spell_context_with_variant(
        cls,
        *,
        spell_context: dict[str, Any],
        variant: Any,
        participant: dict[str, Any],
        target_variant_assignments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _validate_cast_prerequisites(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        actor_user_id: str,
        is_gm: bool,
        *,
        clear_pending_attack: bool = True,
    ) -> tuple[CombatState | None, dict[str, Any], Any]: ...

    @classmethod
    def _resolve_player_spell_context(
        cls,
        db: Session,
        session_id: str,
        attacker: dict[str, Any],
        attacker_model: Any,
        req: Any,
    ) -> dict[str, Any]: ...

    @classmethod
    def _validate_modal_target_variant_assignments(
        cls,
        *,
        req: Any,
        spell_context: dict[str, Any],
        state: CombatState,
    ) -> list[dict[str, Any]] | None: ...

    @classmethod
    def _validate_modal_variant_spatial_targets(
        cls,
        *,
        db: Session,
        state: CombatState,
        attacker: dict[str, Any],
        spell_context: dict[str, Any],
        assignments: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_modal_multi_target_cast(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
        validated_assignments: list[dict[str, Any]],
        *,
        spatial_results_by_participant_id: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _validate_plain_multi_target_refs(
        cls,
        *,
        req: Any,
        spell_context: dict[str, Any],
        state: CombatState,
    ) -> list[dict[str, Any]] | None: ...

    @classmethod
    def _validate_plain_multi_target_spatial(
        cls,
        *,
        db: Session,
        state: CombatState,
        attacker: dict[str, Any],
        spell_context: dict[str, Any],
        targets: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_plain_multi_target_automation_cast(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
        targets: list[dict[str, Any]],
        *,
        spatial_results: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _get_spell_variants_map(
        cls, spell_context: dict[str, Any]
    ) -> dict[str, Any]: ...

    @classmethod
    def _validate_instance_targets(
        cls,
        *,
        req: Any,
        spell_context: dict[str, Any],
        state: CombatState,
    ) -> list[dict[str, Any]] | None: ...

    @classmethod
    def _validate_instance_spatial_targets(
        cls,
        *,
        db: Session,
        state: CombatState,
        attacker: dict[str, Any],
        spell_context: dict[str, Any],
        validated_targets: list[dict[str, Any]],
        session_id: str,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_multi_instance_cast(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
        validated_targets: list[dict[str, Any]],
        *,
        spatial_results_by_target_ref: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _resolve_supported_area_spell_spec(
        cls,
        spell_context: dict[str, Any],
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _normalize_area_shape(cls, value: object) -> str | None: ...

    @classmethod
    def _build_limiar_map_client(cls) -> Any: ...

    @classmethod
    async def _cast_spell_via_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict[str, Any],
        attacker_model: Any,
        actor_user_id: str,
        is_gm: bool,
        req: Any,
        state: CombatState,
        spell_context: dict[str, Any],
        target_participant: dict[str, Any],
    ) -> dict[str, Any] | None: ...

    @classmethod
    async def _cast_spell_via_declarative_effects(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict[str, Any],
        attacker_model: Any,
        actor_user_id: str,
        is_gm: bool,
        req: Any,
        state: CombatState,
        spell_context: dict[str, Any],
        target_participant: dict[str, Any],
        effect_group_id: str | None = None,
    ) -> dict[str, Any] | None: ...

    @classmethod
    def _resolve_instance_attack(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        req: Any,
        is_gm: bool,
        *,
        targeting_result: Any | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _resolve_instance_direct(
        cls,
        db: Session,
        state: CombatState,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        req: Any,
    ) -> dict[str, Any]: ...

    @classmethod
    def _is_shielded_for_magic_missile(
        cls,
        participant: dict[str, Any] | None,
    ) -> bool: ...

    @classmethod
    def _resolve_saving_throw_spell(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        req: Any,
        is_gm: bool,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
        save_success_outcome: str | None = None,
        targeting_result: Any | None = None,
    ) -> Any: ...

    @classmethod
    def _spell_context_has_declarative_effects(
        cls,
        spell_context: dict[str, Any],
    ) -> bool: ...

    @classmethod
    def _apply_declarative_spell_effects(
        cls,
        *,
        state: CombatState,
        attacker: dict[str, Any],
        target_participant: dict[str, Any],
        spell_context: dict[str, Any],
        effect_group_id: str | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _build_applied_declarative_effects_by_target(
        cls,
        effects: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...

    @classmethod
    def _apply_temp_hp_from_granted_effects(
        cls,
        db: Session,
        state: CombatState,
        applied_effects: list[dict[str, Any]],
    ) -> None: ...

    @classmethod
    def _resolve_spell_attack(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        req: Any,
        is_gm: bool,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
        targeting_result: Any | None = None,
    ) -> Any: ...

    @classmethod
    def _apply_spell_attack_delayed_damage_effect(
        cls,
        *,
        target_participant: dict[str, Any],
        spell_context: dict[str, Any],
        attacker: dict[str, Any],
    ) -> bool | None: ...

    @classmethod
    def _upsert_shield_temp_ac_effect(
        cls,
        participant: dict[str, Any],
        *,
        source_participant_id: str | None,
    ) -> None: ...

    @classmethod
    def _resolve_direct_effect_spell(
        cls,
        db: Session,
        state: CombatState,
        *,
        attacker: dict[str, Any],
        target_p: dict[str, Any],
        spell_context: dict[str, Any],
        req: Any,
        spell_mode: str,
        effect_kind: str | None,
        effect_bonus: int,
        effect_roll_required: bool,
    ) -> Any: ...

    @classmethod
    def get_inventory_item_charges_current(
        cls,
        inventory_item: Any,
        source_item: Any | None,
    ) -> int | None: ...

    @classmethod
    def _build_multi_instance_log_message(
        cls,
        *,
        attacker: dict[str, Any],
        spell_context: dict[str, Any],
        outcomes: list[dict[str, Any]],
        was_overridden: bool,
        action_cost: str,
    ) -> str: ...

    @classmethod
    def _is_hostile_team_context(
        cls, attacker: dict[str, Any], target_participant: dict[str, Any]
    ) -> bool: ...

    @classmethod
    def _require_pending_attack(
        cls,
        participant: dict[str, Any],
        pending_attack_id: str,
        *,
        expected_type: str,
    ) -> dict[str, Any]: ...

    @classmethod
    def _build_concentration_roll_kwargs(
        cls, roll_source: str, manual_roll: int | None
    ) -> dict[str, Any]: ...

    @classmethod
    async def _emit_log(cls, session_id: str, log_payload: dict[str, Any]) -> None: ...

    @classmethod
    def _get_combat_action_for_entity(
        cls, db: Session, session_entity_id: str, combat_action_id: str
    ) -> tuple[Any, CampaignEntity, Any]: ...

    @classmethod
    def _resolve_entity_combat_action(
        cls, db: Session, session_id: str, npc: CampaignEntity, action: Any
    ) -> dict[str, Any]: ...

    @classmethod
    def _precheck_dragonborn_breath_weapon(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        actor: dict[str, Any],
        req: Any,
    ) -> None: ...

    @classmethod
    async def _action_dragonborn_breath_weapon(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        actor: dict[str, Any],
        req: Any,
    ) -> dict[str, Any]: ...

    @classmethod
    def _consume_turn_resource(
        cls,
        participant: dict[str, Any],
        resource: str,
        *,
        is_gm: bool,
        override_resource_limit: bool = False,
    ) -> bool: ...

    @classmethod
    def _consume_player_spell_slot(
        cls,
        attacker_model: Any,
        slot_level: int,
    ) -> None: ...

    @classmethod
    def _generate_uuid(cls) -> str: ...

    @classmethod
    async def resolve_fall(
        cls,
        db: Session,
        session_id: str,
        participant_id: str,
        height_meters: float,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _expire_effects_for_participant(
        cls,
        session_id: str,
        state: CombatState,
        participant_id: str,
        trigger: str,
    ) -> list[dict[str, Any]]: ...

    @classmethod
    def _prune_expired_timed_combat_effects(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        *,
        game_time_seconds: int,
    ) -> dict[str, Any]: ...

    @classmethod
    def _clear_concentration_for_source(
        cls,
        state: CombatState,
        *,
        source_participant_id: str,
        db: Session | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _clear_concentration_for_participant_status(
        cls,
        state: CombatState | None,
        *,
        source_participant_id: str | None,
        db: Session | None = None,
    ) -> dict[str, Any]: ...

    @classmethod
    def _ensure_active_combat_time_accounting_started(
        cls, db: Session, session_id: str, state: CombatState
    ) -> None: ...

    @classmethod
    def _reset_turn_resources(cls, participant: dict[str, Any]) -> None: ...

    @classmethod
    def _is_player_dead_state(cls, data: dict[str, Any] | None) -> bool: ...

    @classmethod
    def _reset_death_saves(cls, data: dict[str, Any]) -> None: ...

    @classmethod
    def _validate_distance_participant_refs(
        cls,
        state: CombatState,
        entries: Any,
    ) -> None: ...

    @classmethod
    def _apply_distance_entries(cls, state: CombatState, entries: Any) -> None: ...

    @classmethod
    def _sync_all_participant_statuses(cls, db: Session, state: CombatState) -> None: ...

    @classmethod
    def _remove_effect_group(
        cls,
        state: CombatState,
        *,
        concentration_group: str,
    ) -> dict[str, Any]: ...

    @classmethod
    def _sync_area_effects_if_changed(
        cls,
        session_id: str,
        state: CombatState,
        area_removed: list[dict[str, Any]],
    ) -> None: ...

    @classmethod
    async def _cast_area_spell(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        *,
        attacker: dict[str, Any],
        attacker_model: Any,
        actor_user_id: str,
        is_gm: bool,
        state: CombatState,
        spell_context: dict[str, Any],
        area_spec: dict[str, int | str],
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_teleport_spell(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_no_external_target_cast(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _resolve_cast_resolution(
        cls,
        db: Session,
        session_id: str,
        req: Any,
        state: CombatState,
        attacker: dict[str, Any],
        attacker_model: Any,
        spell_context: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]: ...

    @classmethod
    async def _commit_cast_result(
        cls,
        db: Session,
        session_id: str,
        state: CombatState,
        attacker: dict[str, Any],
        spell_context: dict[str, Any],
        resolution: dict[str, Any],
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]: ...
