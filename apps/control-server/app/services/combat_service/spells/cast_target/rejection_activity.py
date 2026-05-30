from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import select

from app.models.campaign_member import CampaignMember
from app.models.session import Session as CampaignSession
from app.models.session_command_event import SessionCommandEvent

from ...targeting_diagnostics import INVALID_TARGET_TYPE, MAP_UNREACHABLE, NO_LINE_OF_EFFECT, NO_LINE_OF_SIGHT, TARGET_OUT_OF_REACH


class CastTargetRejectionActivityMixin:
    @classmethod
    def _map_spell_rejection_reason(cls, reason: str | None) -> str:
        if reason == TARGET_OUT_OF_REACH:
            return "out_of_range"
        if reason == NO_LINE_OF_SIGHT:
            return "blocked_line_of_sight"
        if reason == NO_LINE_OF_EFFECT:
            return "blocked_line_of_effect"
        if reason in (INVALID_TARGET_TYPE, "target_not_found"):
            return "invalid_target"
        if reason == MAP_UNREACHABLE:
            return "missing_map_data"
        return "invalid_target"

    @classmethod
    def _build_spell_rejection_message(
        cls,
        *,
        actor_name: str,
        spell_name: str,
        reason: str,
        target_name: str | None = None,
        instance_index: int | None = None,
        is_area: bool = False,
    ) -> str:
        subject = f"{actor_name} tentou conjurar {spell_name}"
        if instance_index is not None:
            subject = f"{subject}, mas Feixe {instance_index}"
            if target_name:
                subject = f"{subject} contra {target_name}"
        elif is_area:
            subject = f"{subject}, mas a origem da area"
        elif target_name:
            subject = f"{subject} em {target_name}"

        if reason == "blocked_line_of_sight":
            return f"{subject} estava sem linha de visao."
        if reason == "blocked_line_of_effect":
            return f"{subject} estava sem linha de efeito."
        if reason == "out_of_range":
            return f"{subject} estava fora do alcance."
        if reason == "missing_map_data":
            return f"{subject} nao pode ser resolvido por falta de dados do mapa."
        return f"{subject} tinha um alvo invalido."

    @classmethod
    def _record_spell_cast_rejected_activity(
        cls,
        db,
        *,
        session_id: str,
        actor_user_id: str,
        actor_ref_id: str,
        actor_display_name: str,
        spell_context: dict,
        reason: str,
        target_ref_id: str | None = None,
        target_display_name: str | None = None,
        instance_index: int | None = None,
        area_origin: dict | None = None,
    ) -> None:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            return
        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == actor_user_id,
            )
        ).first()
        if not member or not member.id:
            return

        message = cls._build_spell_rejection_message(
            actor_name=actor_display_name,
            spell_name=str(spell_context.get("spell_name") or "magia"),
            reason=reason,
            target_name=target_display_name,
            instance_index=instance_index,
            is_area=area_origin is not None,
        )
        payload = {
            "eventType": "spell_cast_rejected",
            "actorRefId": actor_ref_id,
            "actorDisplayName": actor_display_name,
            "spellId": spell_context.get("spell_canonical_key"),
            "spellName": spell_context.get("spell_name"),
            "targetRefId": target_ref_id,
            "targetDisplayName": target_display_name,
            "instanceIndex": instance_index,
            "areaOrigin": area_origin,
            "reason": reason,
            "message": message,
        }
        db.add(
            SessionCommandEvent(
                id=str(uuid4()),
                session_id=session_entry.id,
                user_id=actor_user_id,
                member_id=member.id,
                actor_name=actor_display_name,
                command_type="spell_cast_rejected",
                payload_json=payload,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
