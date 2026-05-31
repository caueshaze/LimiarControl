from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.roll_resolution import resolve_skill_check
from app.services.silent_image import (
    find_silent_image_effect,
    mark_illusion_discerned,
    update_illusion,
)

from ..exceptions import CombatServiceError
from ..host_protocol import CombatServiceHostProtocol
from ..limiar_map_projection import maybe_sync_active_area_effects_to_limiar_map


if TYPE_CHECKING:
    _IllusionsBase = CombatServiceHostProtocol
else:
    _IllusionsBase = object


class IllusionsMixin(_IllusionsBase):
    """Interaction endpoints for persistent visual illusions (Silent Image et al.)."""

    @classmethod
    async def resolve_illusion_investigation(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        illusion_id: str,
        actor_user_id: str,
        is_gm: bool,
        roll_source: str = "system",
        manual_roll: int | None = None,
        manual_rolls: list[int] | None = None,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        actor = cls._resolve_actor_participant(
            state, actor_user_id, is_gm, actor_participant_id,
        )
        cls._require_actor_status(
            actor,
            ("active",),
            "Only active participants can examine an illusion.",
        )

        # Validate the illusion exists/active BEFORE consuming the action.
        illusion = find_silent_image_effect(state, illusion_id)
        if illusion is None:
            raise CombatServiceError("No active illusion matches that id.", 400)
        investigation_dc = cls._safe_int(illusion.get("investigation_dc"), 0)
        if investigation_dc <= 0:
            raise CombatServiceError("Illusion is missing a valid investigation DC.", 400)

        was_overridden = cls._consume_turn_resource(
            actor,
            "action",
            is_gm=is_gm,
            override_resource_limit=override_resource_limit,
        )

        roll_result = resolve_skill_check(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                actor["ref_id"],
                actor["kind"],
                actor["display_name"],
            ),
            "investigation",
            dc=investigation_dc,
            roll_source=roll_source,
            manual_roll=manual_roll,
            manual_rolls=manual_rolls,
        )
        roll_result.is_gm_roll = is_gm
        discerned = bool(roll_result.success)

        if discerned:
            mark_illusion_discerned(state, illusion_id, actor["ref_id"])
            flag_modified(state, "active_area_effects")

        db.add(state)
        db.commit()
        db.refresh(state)
        if discerned:
            maybe_sync_active_area_effects_to_limiar_map(session_id, state)
        await cls._emit_state(session_id, state)

        spell_name = illusion.get("source_spell_name") or "Illusion"
        outcome = "discerniu a ilusão" if discerned else "não percebeu nada de errado"
        message = (
            f"{actor['display_name']} examinou {spell_name}: teste de Inteligência "
            f"(Investigação) {roll_result.total} vs CD {investigation_dc} — {outcome}."
        )
        if was_overridden:
            message = f"[OVERRIDE: Action limit ignored] {message}"
        await cls._emit_log(
            session_id,
            {
                "message": message,
                "source": "illusion_investigation",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )

        return {
            "illusionId": illusion_id,
            "sourceSpellKey": illusion.get("source_spell_canonical_key"),
            "investigationCheck": {
                "ability": "intelligence",
                "skill": "investigation",
                "dc": investigation_dc,
                "success": discerned,
                "total": roll_result.total,
                "rollResult": roll_result,
            },
            "discerned": discerned,
            "actorRefId": actor["ref_id"],
            "actionConsumed": True,
            "isOverride": was_overridden,
        }

    @classmethod
    async def resolve_illusion_update(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_participant_id: str | None,
        illusion_id: str,
        actor_user_id: str,
        is_gm: bool,
        point: dict | None = None,
        appearance: dict | None = None,
        override_resource_limit: bool = False,
    ) -> dict:
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        illusion = find_silent_image_effect(state, illusion_id)
        if illusion is None:
            raise CombatServiceError("No active illusion matches that id.", 400)
        if point is None and appearance is None:
            raise CombatServiceError("Provide a new point and/or appearance to update.", 400)

        action_consumed = False
        was_overridden = False
        if not is_gm:
            actor = cls._resolve_actor_participant(
                state, actor_user_id, is_gm, actor_participant_id,
            )
            if actor.get("id") != illusion.get("caster_participant_id"):
                raise CombatServiceError(
                    "Only the caster (or the GM) can move or alter this illusion.", 403,
                )
            cls._require_actor_status(
                actor,
                ("active",),
                "You can only move or alter the illusion on your turn.",
            )
            current = state.participants[state.current_turn_index]
            if current.get("id") != actor.get("id"):
                raise CombatServiceError(
                    "You can only move or alter the illusion on your turn.", 403,
                )
            was_overridden = cls._consume_turn_resource(
                actor,
                "action",
                is_gm=is_gm,
                override_resource_limit=override_resource_limit,
            )
            action_consumed = True
            flag_modified(state, "participants")

        update_illusion(state, illusion_id, point=point, appearance=appearance)
        flag_modified(state, "active_area_effects")

        db.add(state)
        db.commit()
        db.refresh(state)
        maybe_sync_active_area_effects_to_limiar_map(session_id, state)
        await cls._emit_state(session_id, state)

        spell_name = illusion.get("source_spell_name") or "Illusion"
        message = f"{spell_name} foi movida ou alterada pelo conjurador."
        if was_overridden:
            message = f"[OVERRIDE: Action limit ignored] {message}"
        await cls._emit_log(
            session_id,
            {
                "message": message,
                "source": "illusion_update",
                "is_override": was_overridden,
                "overridden_resource": "action" if was_overridden else None,
            },
        )

        return {
            "illusionId": illusion_id,
            "position": illusion.get("origin_point"),
            "appearance": illusion.get("appearance"),
            "discernedByRefIds": illusion.get("discerned_by_ref_ids") or [],
            "actionConsumed": action_consumed,
            "isOverride": was_overridden,
        }

    @classmethod
    async def resolve_illusion_reveal_by_interaction(
        cls,
        db: Session,
        session_id: str,
        *,
        actor_ref_id: str,
        illusion_id: str,
        is_gm: bool,
    ) -> dict:
        if not is_gm:
            raise CombatServiceError(
                "Only the GM can reveal an illusion by physical interaction.", 403,
            )
        state = cls.get_state(db, session_id)
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)
        cls._require_active(state)

        illusion = find_silent_image_effect(state, illusion_id)
        if illusion is None:
            raise CombatServiceError("No active illusion matches that id.", 400)
        if cls._get_participant_by_ref(state, actor_ref_id) is None:
            raise CombatServiceError("Actor is not a participant in this combat.", 400)

        marked = mark_illusion_discerned(state, illusion_id, actor_ref_id)
        flag_modified(state, "active_area_effects")

        db.add(state)
        db.commit()
        db.refresh(state)
        maybe_sync_active_area_effects_to_limiar_map(session_id, state)
        await cls._emit_state(session_id, state)

        spell_name = illusion.get("source_spell_name") or "Illusion"
        await cls._emit_log(
            session_id,
            {
                "message": (
                    f"{actor_ref_id} interagiu fisicamente com {spell_name} e percebeu "
                    f"que é uma ilusão."
                ),
                "source": "illusion_reveal",
            },
        )

        return {
            "illusionId": illusion_id,
            "discerned": marked,
            "actorRefId": actor_ref_id,
            "discernedByRefIds": illusion.get("discerned_by_ref_ids") or [],
        }
