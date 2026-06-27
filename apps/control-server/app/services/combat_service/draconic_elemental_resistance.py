from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified

from app.services.draconic_ancestry import (
    ELEMENTAL_AFFINITY_RESISTANCE_DURATION_SECONDS,
    ELEMENTAL_AFFINITY_RESISTANCE_EFFECT_KIND,
    ELEMENTAL_AFFINITY_RESISTANCE_SOURCE,
    resolve_draconic_lineage_state,
)
from app.services.game_time import get_game_time_seconds
from app.services.session_state_finalize import finalize_session_state_data
from app.services.sorcerer_progression import (
    SORCERY_POINTS_RESOURCE_KEY,
    apply_sorcery_points_canonical_state,
    get_sorcery_points_remaining,
)

from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


DRACONIC_ELEMENTAL_RESISTANCE_ACTION_ID = "draconic_elemental_resistance"


class CombatDraconicElementalResistanceMixin(CombatServiceHostProtocol):
    @classmethod
    async def activate_draconic_elemental_resistance(
        cls,
        db,
        session_id: str,
        *,
        actor_participant_id: str | None,
        actor_user_id: str,
        is_gm: bool,
    ) -> dict:
        """Spend 1 sorcery point to gain resistance to the lineage's damage type
        for 1 minute (Elemental Affinity, Draconic Bloodline 6+)."""
        state = cls.get_state(db, session_id)
        cls._require_active(state)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        actor = cls._resolve_actor_participant(state, actor_user_id, is_gm, actor_participant_id)
        cls._require_actor_status(
            actor, ("active",), "You can only activate Elemental Affinity when active."
        )
        if actor.get("kind") != "player":
            raise CombatServiceError("Only players can activate Elemental Affinity.", 400)

        actor_state, *_ = cls._get_stats(db, actor["ref_id"], actor["kind"], session_id)
        data = apply_sorcery_points_canonical_state(
            cls._as_dict(actor_state.state_json) if actor_state is not None else {}
        )

        lineage = resolve_draconic_lineage_state(data)
        resistance_type = lineage.get("resistanceType")
        if not lineage.get("hasElementalAffinity") or not resistance_type:
            raise CombatServiceError(
                "Elemental Affinity is not available for this character.", 400
            )

        remaining = get_sorcery_points_remaining(data)
        if remaining <= 0:
            raise CombatServiceError("No sorcery points remaining.", 400)

        class_resources = dict(data.get("classResources") or {})
        resource = dict(class_resources.get(SORCERY_POINTS_RESOURCE_KEY) or {})
        resource["usesRemaining"] = remaining - 1
        class_resources[SORCERY_POINTS_RESOURCE_KEY] = resource
        data["classResources"] = class_resources

        game_time_seconds = get_game_time_seconds(session_id, db)
        expires_at = game_time_seconds + ELEMENTAL_AFFINITY_RESISTANCE_DURATION_SECONDS

        effects = list(data.get("active_spell_effects") or [])
        # Refresh rather than stack: a single elemental-affinity resistance for
        # the lineage type is enough; re-activating extends the timer.
        effects = [
            effect
            for effect in effects
            if not (
                isinstance(effect, dict)
                and effect.get("kind") == ELEMENTAL_AFFINITY_RESISTANCE_EFFECT_KIND
                and str(effect.get("damage_type") or "").strip().lower() == resistance_type
            )
        ]
        effects.append(
            {
                "id": str(uuid4()),
                "kind": ELEMENTAL_AFFINITY_RESISTANCE_EFFECT_KIND,
                "source": ELEMENTAL_AFFINITY_RESISTANCE_SOURCE,
                "damage_type": resistance_type,
                "label": f"Resistência elemental ({resistance_type})",
                "duration_type": "timed",
                "created_at_game_time_seconds": game_time_seconds,
                "expires_at_game_time_seconds": expires_at,
            }
        )
        data["active_spell_effects"] = effects

        actor_state.state_json = finalize_session_state_data(
            data, game_time_seconds=game_time_seconds
        )
        flag_modified(actor_state, "state_json")
        db.add(actor_state)
        db.commit()
        db.refresh(actor_state)
        db.refresh(state)

        await cls._emit_player_state_update(db, session_id, actor["ref_id"], actor_state)
        await cls._emit_state(session_id, state)

        points_remaining = get_sorcery_points_remaining(cls._as_dict(actor_state.state_json))
        message = (
            f"{actor['display_name']} gasta 1 ponto de feitiçaria e ganha "
            f"resistência a {resistance_type} por 1 minuto "
            f"(Afinidade Elemental). Pontos restantes: {points_remaining}."
        )
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
            "action": DRACONIC_ELEMENTAL_RESISTANCE_ACTION_ID,
            "actor_name": actor["display_name"],
            "damage_type": resistance_type,
            "expires_at_game_time_seconds": expires_at,
            "duration_seconds": ELEMENTAL_AFFINITY_RESISTANCE_DURATION_SECONDS,
            "sorcery_points_remaining": points_remaining,
            "message": message,
        }
