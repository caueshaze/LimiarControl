from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.goodberry_inventory import (
    build_goodberry_expiration,
    grant_catalog_item_to_player_inventory,
)
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _HuntersMarkInventoryBase = CombatServiceHostProtocol
else:
    _HuntersMarkInventoryBase = object


class HuntersMarkInventoryAutomationMixin(_HuntersMarkInventoryBase):
    @classmethod
    async def _cast_hunters_mark_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict:
        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id, state, result["removed_area_effects"],
        )
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        metadata = {
            "concentration": True,
            "concentration_group": concentration_group,
            "source_spell_key": "hunters_mark",
            "marked_target_participant_id": target_participant["id"],
            "bonus_damage_dice": "1d6",
        }
        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="manual",
                expires_at_participant_id=attacker["id"],
                metadata=metadata,
                display_label=spell_name,
            ),
        )
        cls._append_effect_to_participant(
            target_participant,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="manual",
                expires_at_participant_id=target_participant["id"],
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "hunters_mark",
                    "mark_owner_participant_id": attacker["id"],
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = f"{spell_name} aplicada em {target_participant['display_name']}."
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_participant['display_name']}. "
                f"A marca está ativa."
            ),
        )

    @classmethod
    async def _cast_goodberry_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict:
        session_entry = cls._get_session_entry(db, session_id)
        if not session_entry:
            raise CombatServiceError("Session not found.", 404)

        inventory_entry = grant_catalog_item_to_player_inventory(
            db,
            session_entry=session_entry,
            player_user_id=attacker["ref_id"],
            system=cls._get_campaign_system_for_session(db, session_id),
            canonical_key="goodberry",
            quantity=10,
            notes="Created by Goodberry",
            expires_at=build_goodberry_expiration(),
            source_spell_canonical_key="goodberry",
        )
        spell_name = spell_context["spell_name"]

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind="player",
            summary_text="10 Bom Fruto foram adicionados ao seu inventário.",
            inventory_refresh_required=True,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e criou 10 Bom Fruto."
            ),
            extra={
                "__inventory_item_id": getattr(inventory_entry, "id", None),
            },
        )

    @classmethod
    async def _cast_purify_food_and_drink_automation(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        attacker_model,
        actor_user_id: str,
        is_gm: bool,
        req,
        state: CombatState,
        spell_context: dict,
        target_participant: dict | None,
    ) -> dict:
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("purify_food_and_drink não possui variantes.", status_code=400)

        spell_name = spell_context["spell_name"]

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=(
                f"{spell_name}: alimentos e bebidas não mágicos "
                "em uma esfera de 1,5m foram purificados."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name}, "
                "purificando alimentos e bebidas na área."
            ),
            extra={
                "utility": "purify_food_and_drink",
                "purified_food_and_drink": True,
                "radius_meters": 1.5,
                "instantaneous": True,
            },
        )
