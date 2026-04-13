from __future__ import annotations

from datetime import datetime, timezone
import random
from math import floor
from typing import Any
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.core.config import settings
from app.integrations import LimiarMapClient, LimiarMapClientError
from app.models.base_item import BaseItemKind, BaseItemWeaponRangeType
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item, ItemType
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAreaPreviewRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatMapPreviewState,
    CombatResolveDamageRequest,
    CombatResolveSpellEffectRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.draconic_ancestry import resolve_elemental_affinity
from app.services.magic_item_effects import (
    consume_inventory_item_charge,
    get_magic_item_effect,
    get_inventory_item_charges_current,
    get_magic_item_spell_key,
)
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.session_state_finalize import finalize_session_state_data
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.schemas.roll import RollActorStats, RollResult

from ..combat_targeting import get_combat_targeting_service
from ..exceptions import CombatServiceError, _parse_dice
from ..targeting_requirements import (
    resolve_spell_targeting_requirements,
    resolve_weapon_targeting_requirements,
)
from ..targeting_intent import AreaTargetingIntent, SpellCastIntent, WeaponAttackIntent
from ..unit_conversion import meters_to_cells



class AreaTargetingMixin:
    @classmethod
    def _normalize_area_shape(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if normalized in {"sphere", "cone", "line"}:
            return normalized
        return None

    @classmethod
    def _resolve_supported_area_spell_spec(
        cls,
        spell_context: dict[str, Any],
    ) -> dict[str, int | str] | None:
        target_mode = cls._normalize_area_shape(spell_context.get("target_mode"))
        if target_mode is None:
            return None

        spell_key = cls._normalize_lookup(spell_context.get("spell_canonical_key"))
        spec = cls._SUPPORTED_AREA_SPELL_SPECS.get(spell_key)
        if spec is None:
            return None

        shape = cls._normalize_area_shape(spec.get("shape"))
        size_meters = cls._safe_optional_int(spec.get("size_meters"))
        if shape is None or size_meters is None or size_meters <= 0:
            return None
        if shape != target_mode:
            return None

        return {
            "shape": shape,
            "size_meters": size_meters,
            "range_meters": cls._safe_optional_int(spell_context.get("range_meters")),
        }

    @classmethod
    def _build_limiar_map_client(cls) -> LimiarMapClient:
        if not settings.limiar_map_enabled:
            raise CombatServiceError(
                "Area targeting map integration is disabled.",
                503,
            )
        return LimiarMapClient(
            base_url=settings.limiar_map_base_url,
            timeout_seconds=settings.limiar_map_timeout_seconds,
        )

    @classmethod
    def _resolve_area_origin_cell(
        cls,
        *,
        actor_ref_id: str,
        map_state,
        requested_origin_cell,
    ) -> dict[str, int]:
        if requested_origin_cell is not None:
            return {
                "x": requested_origin_cell.x,
                "y": requested_origin_cell.y,
            }

        source_token = next(
            (token for token in map_state.tokens if token.combatant_id == actor_ref_id),
            None,
        )
        if source_token is None:
            raise CombatServiceError("Actor is not linked to a map token.", 400)
        if source_token.position_x is None or source_token.position_y is None:
            raise CombatServiceError("Actor map token is missing a position.", 400)
        return {
            "x": source_token.position_x,
            "y": source_token.position_y,
        }

    @classmethod
    def get_area_targeting_map_state(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ) -> CombatMapPreviewState:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        actor = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )
        cls._require_actor_status(actor, ("active",), "You can only target an area when active.")

        client = cls._build_limiar_map_client()
        try:
            map_state = client.get_session_state(session_id)
        except LimiarMapClientError as exc:
            raise CombatServiceError(
                f"Area targeting map state is unavailable: {exc}",
                503,
            ) from exc

        if map_state.grid_width is None or map_state.grid_height is None:
            raise CombatServiceError("LimiarMap state is missing grid dimensions.", 503)

        return CombatMapPreviewState(
            session_id=map_state.session_id,
            version=map_state.version,
            grid_width=map_state.grid_width,
            grid_height=map_state.grid_height,
            tokens=[
                {
                    "token_id": token.token_id,
                    "label": token.label or token.token_id,
                    "position": {
                        "x": token.position_x,
                        "y": token.position_y,
                    },
                    "combatant_id": token.combatant_id,
                    "controller_type": token.controller_type,
                }
                for token in map_state.tokens
                if token.position_x is not None and token.position_y is not None
            ],
            obstacles=[
                {
                    "cells": [
                        {"x": cell.x, "y": cell.y}
                        for cell in obstacle.cells
                    ],
                    "blocks_movement": obstacle.blocks_movement,
                    "blocks_vision": obstacle.blocks_vision,
                    "blocks_effect": obstacle.blocks_effect,
                    "cover": obstacle.cover,
                }
                for obstacle in map_state.obstacles
            ],
        )

    @classmethod
    def preview_area_spell_targeting(
        cls,
        db: Session,
        session_id: str,
        req: CombatAreaPreviewRequest,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict[str, Any]:
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            req.actor_participant_id,
        )
        cls._require_actor_status(attacker, ("active",), "You can only target an area when active.")
        if attacker["kind"] != "player":
            raise CombatServiceError("Only players can preview this spell casting flow.", 400)

        attacker_model, *_ = cls._get_stats(db, attacker["ref_id"], attacker["kind"], session_id)
        attacker_data = cls._as_dict(attacker_model.state_json)
        if cls._as_dict(attacker_data.get("wildShape")).get("active"):
            raise CombatServiceError("Cannot cast spells while in Wild Shape.", 400)

        spell_context = cls._resolve_player_spell_context(
            db,
            session_id,
            attacker,
            attacker_model,
            CombatCastSpellRequest(
                actor_participant_id=req.actor_participant_id,
                target_ref_id=req.target_ref_id,
                origin_cell=req.origin_cell,
                anchor_cell=req.anchor_cell,
                inventory_item_id=req.inventory_item_id,
                spell_id=req.spell_id,
                spell_canonical_key=req.spell_canonical_key,
                spell_mode=req.spell_mode,
                slot_level=req.slot_level,
            ),
        )
        area_spec = cls._resolve_supported_area_spell_spec(spell_context)
        if area_spec is None:
            raise CombatServiceError(
                "This area spell is not configured for map targeting yet.",
                400,
            )

        client = cls._build_limiar_map_client()
        try:
            map_state = client.get_session_state(session_id)
            origin_cell = cls._resolve_area_origin_cell(
                actor_ref_id=attacker["ref_id"],
                map_state=map_state,
                requested_origin_cell=req.origin_cell,
            )
            # Convert meters → cells at the Control → Map boundary.
            preview_range_meters = cls._safe_optional_int(area_spec.get("range_meters"))
            preview_size_meters = cls._safe_int(area_spec.get("size_meters"), 0)
            preview = client.preview_area_targeting(
                session_id=session_id,
                action_id=f"preview:{uuid4()}",
                combatant_id=attacker["ref_id"],
                shape=str(area_spec["shape"]),
                origin_cell=origin_cell,
                anchor_cell={"x": req.anchor_cell.x, "y": req.anchor_cell.y},
                range_cells=(
                    meters_to_cells(preview_range_meters) if preview_range_meters is not None else None
                ),
                size_cells=meters_to_cells(preview_size_meters),
                requires_sight=bool(spell_context.get("requires_point_sight")),
                requires_effect=bool(spell_context.get("requires_point_effect")),
            )
        except LimiarMapClientError as exc:
            raise CombatServiceError(
                f"Area targeting preview is unavailable: {exc}",
                503,
            ) from exc

        return {
            "is_valid": preview.is_valid,
            "reason": preview.reason,
            "shape": preview.shape,
            "affected_cells": [
                {"x": cell.x, "y": cell.y}
                for cell in preview.affected_cells
            ],
            "affected_target_ref_ids": list(preview.affected_combatant_ids),
            "affected_token_ids": list(preview.affected_token_ids),
            "map_version": preview.version,
        }
