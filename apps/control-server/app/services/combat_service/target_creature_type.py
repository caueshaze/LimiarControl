from __future__ import annotations

from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity_shared import CreatureType
from app.services.wild_shape_catalog import get_form


_KNOWN_CREATURE_TYPES = set(CreatureType.__args__)  # type: ignore[attr-defined]


class CombatTargetCreatureTypeMixin:
    @classmethod
    def normalize_creature_type(cls, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if normalized not in _KNOWN_CREATURE_TYPES:
            return None
        return normalized

    @classmethod
    def resolve_effective_creature_type(
        cls,
        db: Session,
        session_id: str,
        participant: dict,
    ) -> str | None:
        kind = participant.get("kind")
        ref_id = participant.get("ref_id")
        if not isinstance(kind, str) or not isinstance(ref_id, str):
            return None

        if kind == "player":
            state = db.exec(
                select(SessionState).where(
                    SessionState.session_id == session_id,
                    SessionState.player_user_id == ref_id,
                )
            ).first()
            state_json = state.state_json if state and isinstance(state.state_json, dict) else {}
            wild_shape = state_json.get("wildShape")
            if isinstance(wild_shape, dict) and wild_shape.get("active") is True:
                form_key = wild_shape.get("formKey")
                form = get_form(form_key) if isinstance(form_key, str) else None
                if form is None:
                    return None
                tags = form.tags if isinstance(form.tags, list) else []
                normalized_tags = {str(tag).strip().lower() for tag in tags if isinstance(tag, str)}
                if "beast" in normalized_tags:
                    return "beast"
                return None
            return "humanoid"

        if kind == "session_entity":
            session_entity = db.exec(
                select(SessionEntity).where(SessionEntity.id == ref_id)
            ).first()
            if not session_entity:
                return None
            campaign_entity = db.exec(
                select(CampaignEntity).where(CampaignEntity.id == session_entity.campaign_entity_id)
            ).first()
            if not campaign_entity:
                return None
            return cls.normalize_creature_type(campaign_entity.creature_type)

        return None
