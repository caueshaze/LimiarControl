from __future__ import annotations

import random

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.services.session_state_finalize import finalize_session_state_data

from .exceptions import CombatServiceError


class CombatPlayerDeathSaveMixin:
    @classmethod
    async def death_save(
        cls,
        db: Session,
        session_id: str,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ):
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        attacker_p = cls._resolve_actor_participant(
            state,
            actor_user_id,
            is_gm,
            actor_participant_id,
        )

        if attacker_p["kind"] != "player":
            raise CombatServiceError("Only players roll Death Saves.")
        cls._require_actor_status(
            attacker_p, ("downed",), "You can only roll Death Saves when downed."
        )

        target_model, *_ = cls._get_stats(
            db, attacker_p["ref_id"], attacker_p["kind"], session_id
        )
        data = cls._as_dict(target_model.state_json)
        death_saves = cls._as_dict(data.get("deathSaves"))

        roll = random.randint(1, 20)
        msg = f"rolled a Death Save: {roll}."
        auto_proxy_next_turn = True

        if roll == 1:
            death_saves["failures"] += 2
            msg += " CRITICAL FAILURE (2 Fails)!"
        elif roll == 20:
            data["currentHP"] = 1
            msg += " CRITICAL SUCCESS! (Regains 1 HP, Stands Up!)"
            auto_proxy_next_turn = False
        elif roll >= 10:
            death_saves["successes"] += 1
            msg += " (Success!)"
        else:
            death_saves["failures"] += 1
            msg += " (Failure!)"

        data["deathSaves"] = death_saves
        target_model.state_json = finalize_session_state_data(data)
        status = cls._sync_participant_status(
            db, state, attacker_p["ref_id"], attacker_p["kind"], target_model
        )
        if status == "dead":
            msg += " THE CHARACTER HAS DIED."
        elif status == "stable":
            msg += " THE CHARACTER IS STABILIZED."
        flag_modified(target_model, "state_json")
        db.add(target_model)

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)
        await cls._emit_player_state_update(
            db, session_id, attacker_p["ref_id"], target_model
        )
        await cls._emit_and_persist_log(
            db, session_id, actor_user_id, attacker_p["display_name"],
            {
                "message": f"{attacker_p['display_name']} {msg}",
                "actorUserId": actor_user_id,
                "source": "player_turn" if not is_gm else "gm_override",
            },
        )

        if auto_proxy_next_turn:
            await cls.next_turn(
                db,
                session_id,
                actor_user_id,
                is_gm,
                actor_participant_id=attacker_p.get("id"),
                skip_turn_end_validation=True,
            )
        else:
            await cls._emit_state(session_id, state)

        return {
            "roll": roll,
            "status": attacker_p["status"],
            "death_saves": death_saves,
        }
