from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified

from app.services.dragon_wings import (
    is_dragon_wings_active,
    is_dragon_wings_eligible,
)
from app.services.session_state_finalize import finalize_session_state_data

from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


DRAGON_WINGS_ACTION_ID = "dragon_wings"


class CombatDragonWingsMixin(CombatServiceHostProtocol):
    @classmethod
    async def toggle_dragon_wings(
        cls,
        db,
        session_id: str,
        *,
        activate: bool,
        actor_participant_id: str | None,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        """Sprout or dismiss Dragon Wings (Draconic Bloodline 14+) as a bonus
        action. While active the character has a flying speed equal to its
        walking speed and ignores falling."""
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        cls._require_actor_status(
            actor, ("active",), "You can only use Dragon Wings when active."
        )
        if actor.get("kind") != "player":
            raise CombatServiceError("Only players can use Dragon Wings.", 400)

        actor_state, *_ = cls._get_stats(db, actor["ref_id"], actor["kind"], session_id)
        data = cls._as_dict(actor_state.state_json) if actor_state is not None else {}

        if not is_dragon_wings_eligible(data):
            raise CombatServiceError("Dragon Wings is not available for this character.", 400)

        currently_active = is_dragon_wings_active(data)
        if activate and currently_active:
            raise CombatServiceError("Dragon Wings is already active.", 400)
        if not activate and not currently_active:
            raise CombatServiceError("Dragon Wings is not active.", 400)

        # Both sprouting and dismissing cost a bonus action (RAW).
        was_overridden = cls._consume_turn_resource(actor, "bonus_action", is_gm=is_gm)

        data["dragonWings"] = {"active": activate}
        actor_state.state_json = finalize_session_state_data(data)
        flag_modified(actor_state, "state_json")
        db.add(actor_state)
        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(actor_state)
        db.refresh(state)

        await cls._emit_player_state_update(db, session_id, actor["ref_id"], actor_state)
        await cls._emit_state(session_id, state)

        verb = "faz crescer asas dracônicas e começa a voar" if activate else "dispensa as asas dracônicas"
        message = f"{actor['display_name']} {verb} (ação bônus)."
        if was_overridden:
            message = f"[OVERRIDE: Limite de 'bonus action' ignorado] {message}"
        await cls._emit_and_persist_log(
            db,
            session_id,
            actor_user_id,
            actor.get("display_name"),
            {
                "message": message,
                "actorUserId": actor_user_id,
                "source": "gm_override" if is_gm else "player_turn",
            },
        )

        return {
            "action": DRAGON_WINGS_ACTION_ID,
            "actor_name": actor["display_name"],
            "active": activate,
            "fly_speed_meters": cls._safe_int(
                cls._as_dict(actor_state.state_json).get("flySpeedMeters"), 0
            ),
            "message": message,
        }
