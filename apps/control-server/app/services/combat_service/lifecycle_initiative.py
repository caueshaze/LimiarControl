from __future__ import annotations

from sqlmodel import select

from app.models.campaign_tactical_map import CampaignTacticalMap
from app.models.combat import CombatPhase
from app.models.session import Session as CampaignSession
from app.schemas.campaign import decode_blocked_cells, decode_edge_obstacles, decode_obstacles
from app.schemas.combat import CombatMapSelection

from .exceptions import CombatServiceError
from .limiar_map_projection import maybe_project_combat_start_to_limiar_map


class CombatLifecycleInitiativeMixin:
    @classmethod
    def _participant_requires_initiative(cls, participant: dict) -> bool:
        return participant.get("status") not in cls._INITIATIVE_SKIPPED_STATUSES

    @classmethod
    def _maybe_activate_initiative_order(cls, state) -> bool:
        if state.phase not in (CombatPhase.initiative, "initiative"):
            return False
        pending = [participant for participant in state.participants if cls._participant_requires_initiative(participant)]
        if any(participant.get("initiative") is None for participant in pending):
            return False
        state.participants.sort(key=lambda participant: participant.get("initiative") or 0, reverse=True)
        state.phase = CombatPhase.active
        state.round = 1
        state.current_turn_index = 0
        cls._reset_turn_resources(state.participants[0])
        return True

    @classmethod
    async def apply_initiative_roll(cls, db, session_id: str, actor_kind: str, actor_ref_id: str, initiative: int):
        state = cls.get_state(db, session_id)
        if not state or state.phase in (CombatPhase.ended, "ended") or state.phase not in (CombatPhase.initiative, "initiative"):
            return state
        participant = next((candidate for candidate in state.participants if candidate.get("ref_id") == actor_ref_id and candidate.get("kind") == actor_kind), None)
        if not participant or not cls._participant_requires_initiative(participant):
            return state
        participant["initiative"] = initiative
        transitioned_to_active = cls._maybe_activate_initiative_order(state)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        if transitioned_to_active and state.participants:
            maybe_project_combat_start_to_limiar_map(db, session_id, state)
            await cls._emit_log(session_id, {"message": f"Initiative set! It is now {state.participants[0]['display_name']}'s turn."})
        return state

    @classmethod
    async def start_combat(cls, db, session_id: str, req):
        state = cls.get_state(db, session_id)
        if state:
            db.delete(state)
            db.flush()
        map_selection = cls._resolve_map_selection(db, session_id, req)
        from app.models.combat import CombatState

        new_state = CombatState(
            session_id=session_id,
            phase=CombatPhase.initiative,
            round=1,
            current_turn_index=0,
            participants=[{**participant.model_dump(), "status": "active" if participant.kind == "player" else ("active" if not getattr(participant, "is_defeated", False) else "defeated")} for participant in req.participants],
            map_selection=map_selection,
            use_map=req.useMap,
        )
        if req.initialDistances and not req.useMap:
            cls._validate_distance_participant_refs(new_state, req.initialDistances)
            cls._apply_distance_entries(new_state, req.initialDistances)
        db.add(new_state)
        cls._sync_all_participant_statuses(db, new_state)
        db.commit()
        db.refresh(new_state)
        await cls._emit_state(session_id, new_state)
        await cls._emit_log(session_id, {"message": "Combat started! Roll for initiative."})
        return new_state

    @classmethod
    def _resolve_map_selection(cls, db, session_id: str, req) -> dict:
        requested_kind = req.selectedMap.kind if req.selectedMap is not None else "demo_map"
        if requested_kind == "demo_map":
            return cls._DEMO_MAP_SELECTION.model_dump(mode="json")
        session_entry = db.exec(select(CampaignSession).where(CampaignSession.id == session_id)).first()
        if session_entry is None:
            raise CombatServiceError("Session not found", 404)
        requested_map_id = req.selectedMap.mapId if req.selectedMap is not None else None
        if requested_map_id is None or not requested_map_id.strip():
            raise CombatServiceError("Campaign tactical map id is required", 400)
        campaign_map = db.exec(
            select(CampaignTacticalMap).where(
                CampaignTacticalMap.id == requested_map_id.strip(),
                CampaignTacticalMap.campaign_id == session_entry.campaign_id,
            )
        ).first()
        if campaign_map is None:
            raise CombatServiceError("Campaign tactical map not found", 404)
        if not campaign_map.image_url:
            raise CombatServiceError("Selected tactical map is missing an image", 400)
        if campaign_map.grid_width is None or campaign_map.grid_height is None:
            raise CombatServiceError("Selected tactical map is missing grid dimensions", 400)
        calibration = {
            "x": campaign_map.calibration_x if campaign_map.calibration_x is not None else 0,
            "y": campaign_map.calibration_y if campaign_map.calibration_y is not None else 0,
            "width": campaign_map.calibration_width if campaign_map.calibration_width is not None else 1,
            "height": campaign_map.calibration_height if campaign_map.calibration_height is not None else 1,
        }
        obstacles = decode_obstacles(getattr(campaign_map, "obstacles_json", None))
        selection = CombatMapSelection(
            kind="campaign_map",
            mapId=campaign_map.id,
            mapName=campaign_map.name or "Campaign map",
            imageUrl=campaign_map.image_url,
            gridWidth=campaign_map.grid_width,
            gridHeight=campaign_map.grid_height,
            calibration=calibration,
            obstacles=obstacles,
            edgeObstacles=decode_edge_obstacles(getattr(campaign_map, "edge_obstacles_json", None)),
            blockedCells=decode_blocked_cells(getattr(campaign_map, "blocked_cells_json", None)) if obstacles is None else [],
        )
        return selection.model_dump(mode="json")

    @classmethod
    async def set_initiative(cls, db, session_id: str, req):
        state = cls.get_state(db, session_id)
        if not state:
            raise CombatServiceError("Combat not found", 404)
        if state.phase not in (CombatPhase.initiative, "initiative"):
            raise CombatServiceError("Combat is not in initiative phase")
        updates = {initiative.id: initiative.initiative for initiative in req.initiatives}
        for participant in state.participants:
            if participant["id"] in updates:
                participant["initiative"] = updates[participant["id"]]
        transitioned_to_active = cls._maybe_activate_initiative_order(state)
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_state(session_id, state)
        if transitioned_to_active:
            maybe_project_combat_start_to_limiar_map(db, session_id, state)
            active_name = state.participants[0]["display_name"] if state.participants else "Unknown"
            await cls._emit_log(session_id, {"message": f"Initiative set! It is now {active_name}'s turn."})
        else:
            await cls._emit_log(session_id, {"message": "Initiative updated."})
        return state
