from __future__ import annotations

from dataclasses import dataclass
import logging

from sqlmodel import Session, select

from app.integrations.limiar_map_client import LimiarMapStateResponse
from app.models.campaign_entity import CampaignEntity
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState

from .participant_attributes import (
    resolve_entity_movement_speed,
    resolve_entity_size,
    resolve_player_movement_speed,
    resolve_player_size,
)
from .entity_size import normalize_size_category, SizeCategory
from .unit_conversion import meters_to_movement_cells

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedTokenSyncEntry:
    token_id: str
    combatant_id: str
    movement_speed_cells: int | None
    label: str | None = None
    controller_id: str | None = None
    controller_type: str | None = None
    size_category: str | None = None
    conditions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedTokenSpawnEntry:
    combatant_id: str
    movement_speed_cells: int | None
    label: str | None = None
    kind: str | None = None
    controller_id: str | None = None
    controller_type: str | None = None
    size_category: str | None = None
    conditions: tuple[str, ...] = ()


def _resolve_participant_label(participant: dict) -> str | None:
    value = participant.get("display_name")
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def _resolve_token_controller(
    participant_kind: str,
    participant: dict,
) -> tuple[str | None, str | None]:
    actor_user_id = participant.get("actor_user_id")
    if isinstance(actor_user_id, str) and actor_user_id.strip():
        return actor_user_id.strip(), "player"

    combatant_id = participant.get("ref_id")
    if participant_kind == "player" and isinstance(combatant_id, str):
        cleaned = combatant_id.strip()
        if cleaned:
            return cleaned, "player"

    if participant_kind in ("session_entity", "entity"):
        return "gm-control", "gm"

    return None, None


def _normalize_token_label(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def _resolve_player_character_name(state_json: dict) -> str | None:
    value = state_json.get("characterName")
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return None


def _resolve_expected_token_kind(
    participant_kind: str,
    participant: dict,
) -> str | None:
    if participant_kind == "player":
        return "playerCharacter"

    team = participant.get("team")
    if team == "enemies":
        return "enemy"
    if team in ("players", "allies"):
        return "ally"
    if team == "neutral":
        return "neutral"
    return None


def _extract_explicit_token_id(payload: dict) -> str | None:
    for key in ("mapTokenId", "map_token_id"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for container_key in ("limiarMap", "map"):
        nested = payload.get(container_key)
        if not isinstance(nested, dict):
            continue
        for key in ("tokenId", "mapTokenId", "map_token_id"):
            value = nested.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _extract_participant_conditions(participant: dict) -> list[str]:
    conditions: list[str] = []
    for effect in participant.get("active_effects") or []:
        if effect.get("kind") != "condition":
            continue
        ctype = effect.get("condition_type")
        if isinstance(ctype, str) and ctype.strip():
            code = ctype.strip()
            if code not in conditions:
                conditions.append(code)
    return conditions


def _resolve_token_id(
    map_state: LimiarMapStateResponse,
    *,
    participant_kind: str,
    combatant_id: str,
    explicit_token_id: str | None,
    controller_id: str | None,
    controller_type: str | None,
    label: str | None,
    expected_token_kind: str | None,
    excluded_token_ids: frozenset[str] = frozenset(),
) -> str | None:
    available = [t for t in map_state.tokens if t.token_id not in excluded_token_ids]

    if explicit_token_id:
        token = next((e for e in available if e.token_id == explicit_token_id), None)
        return token.token_id if token is not None else None

    linked_tokens = [e for e in available if e.combatant_id == combatant_id]
    if len(linked_tokens) == 1:
        return linked_tokens[0].token_id
    if len(linked_tokens) > 1:
        return None

    if label:
        normalized_label = _normalize_token_label(label)
        label_tokens = [
            e for e in available
            if _normalize_token_label(e.label) == normalized_label
        ]
        if label_tokens:
            return label_tokens[0].token_id

    if controller_id and controller_type:
        controller_tokens = [
            e for e in available
            if e.controller_type == controller_type and e.controller_id == controller_id
        ]
        if len(controller_tokens) == 1:
            return controller_tokens[0].token_id

    if expected_token_kind:
        kind_tokens = [e for e in available if e.kind == expected_token_kind]
        if kind_tokens:
            return kind_tokens[0].token_id

    if participant_kind == "player":
        player_tokens = [e for e in available if e.controller_type == "player"]
        if len(player_tokens) == 1:
            return player_tokens[0].token_id

    return None


def resolve_sync_entry(
    db: Session,
    session_id: str,
    participant: dict,
    map_state: LimiarMapStateResponse,
    *,
    excluded_token_ids: frozenset[str] = frozenset(),
) -> tuple[ResolvedTokenSyncEntry | None, ResolvedTokenSpawnEntry | None]:
    participant_kind = participant.get("kind")
    combatant_id = participant.get("ref_id")
    if not isinstance(participant_kind, str) or not isinstance(combatant_id, str):
        return None, None

    explicit_token_id: str | None = None
    movement_speed_base: int | None = None
    size_raw: str | None = None
    label = _resolve_participant_label(participant)
    controller_id, controller_type = _resolve_token_controller(
        participant_kind,
        participant,
    )
    expected_token_kind = _resolve_expected_token_kind(
        participant_kind,
        participant,
    )

    if participant_kind == "player":
        state_model = db.exec(
            select(SessionState).where(
                SessionState.session_id == session_id,
                SessionState.player_user_id == combatant_id,
            )
        ).first()
        if state_model and isinstance(state_model.state_json, dict):
            explicit_token_id = _extract_explicit_token_id(state_model.state_json)
            movement_speed_base = resolve_player_movement_speed(state_model.state_json)
            label = _resolve_player_character_name(state_model.state_json) or label
            size_raw = resolve_player_size(state_model.state_json)
    elif participant_kind in ("session_entity", "entity"):
        session_entity = db.exec(
            select(SessionEntity).where(
                SessionEntity.session_id == session_id,
                SessionEntity.id == combatant_id,
            )
        ).first()
        if session_entity:
            if isinstance(session_entity.label, str) and session_entity.label.strip():
                label = session_entity.label.strip()
            overrides = (
                session_entity.overrides
                if isinstance(session_entity.overrides, dict)
                else {}
            )
            explicit_token_id = _extract_explicit_token_id(overrides)
            campaign_entity = db.exec(
                select(CampaignEntity).where(
                    CampaignEntity.id == session_entity.campaign_entity_id
                )
            ).first()
            if (
                label is None
                and campaign_entity is not None
                and isinstance(campaign_entity.name, str)
                and campaign_entity.name.strip()
            ):
                label = campaign_entity.name.strip()
            movement_speed_base = resolve_entity_movement_speed(
                overrides,
                campaign_entity,
            )
            size_raw = resolve_entity_size(overrides, campaign_entity)

    token_id = _resolve_token_id(
        map_state,
        participant_kind=participant_kind,
        combatant_id=combatant_id,
        explicit_token_id=explicit_token_id,
        controller_id=controller_id,
        controller_type=controller_type,
        label=label,
        expected_token_kind=expected_token_kind,
        excluded_token_ids=excluded_token_ids,
    )

    movement_speed_cells = (
        meters_to_movement_cells(movement_speed_base)
        if movement_speed_base is not None
        else None
    )
    size_category_enum = normalize_size_category(size_raw)
    size_category = (
        size_category_enum.value if size_category_enum != SizeCategory.MEDIUM else None
    )
    conditions = _extract_participant_conditions(participant)

    if token_id is not None:
        return ResolvedTokenSyncEntry(
            token_id=token_id,
            combatant_id=combatant_id,
            movement_speed_cells=movement_speed_cells,
            label=label,
            controller_id=controller_id,
            controller_type=controller_type,
            size_category=size_category,
            conditions=tuple(conditions),
        ), None

    # No existing token found — spawn a new one for NPCs only (players must have tokens)
    if participant_kind == "player":
        return None, None

    return None, ResolvedTokenSpawnEntry(
        combatant_id=combatant_id,
        movement_speed_cells=movement_speed_cells,
        label=label,
        kind=expected_token_kind,
        controller_id=controller_id,
        controller_type=controller_type,
        size_category=size_category,
        conditions=tuple(conditions),
    )


def build_sync_entries(
    db: Session,
    session_id: str,
    participants: list[dict],
    map_state: LimiarMapStateResponse,
) -> tuple[list[ResolvedTokenSyncEntry], list[ResolvedTokenSpawnEntry]]:
    resolved_by_token_id: dict[str, ResolvedTokenSyncEntry] = {}
    spawn_entries: list[ResolvedTokenSpawnEntry] = []
    assigned_token_ids: set[str] = set()

    for participant in participants:
        combatant_id = participant.get("ref_id")
        if not isinstance(combatant_id, str) or not combatant_id.strip():
            continue

        sync_entry, spawn_entry = resolve_sync_entry(
            db,
            session_id,
            participant,
            map_state,
            excluded_token_ids=frozenset(assigned_token_ids),
        )

        if sync_entry is not None:
            assigned_token_ids.add(sync_entry.token_id)
            resolved_by_token_id[sync_entry.token_id] = sync_entry
        elif spawn_entry is not None:
            spawn_entries.append(spawn_entry)

    return list(resolved_by_token_id.values()), spawn_entries
