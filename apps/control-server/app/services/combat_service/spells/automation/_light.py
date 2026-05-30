from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.combat import CombatState
from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession
from app.services.game_time import get_game_time_seconds
from app.services.session_state_finalize import finalize_session_state_data
from ...exceptions import CombatServiceError


class LightAutomationMixin:
    @classmethod
    async def _cast_light_automation(
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
        raw_inventory_item_id = getattr(req, "inventory_item_id", None)
        inventory_item_id = (
            raw_inventory_item_id.strip()
            if isinstance(raw_inventory_item_id, str) and raw_inventory_item_id.strip()
            else None
        )
        raw_description = getattr(req, "description", None)
        has_description = isinstance(raw_description, str)
        if (inventory_item_id is None and not has_description) or (
            inventory_item_id is not None and has_description
        ):
            raise CombatServiceError(
                "Luz exige exatamente um alvo narrativo: inventory_item_id ou description.",
                400,
            )

        description: str | None = None
        item_name: str | None = None

        if inventory_item_id is not None:
            session_entry = db.exec(select(CampaignSession).where(CampaignSession.id == session_id)).first()
            if not session_entry:
                raise CombatServiceError("Session not found.", 404)

            item_entry = db.exec(select(InventoryItem).where(InventoryItem.id == inventory_item_id)).first()
            if not item_entry:
                raise CombatServiceError("Inventory item not found.", 404)
            if item_entry.campaign_id != session_entry.campaign_id:
                raise CombatServiceError("Inventory item not found.", 404)
            if session_entry.party_id is not None and item_entry.party_id not in (None, session_entry.party_id):
                raise CombatServiceError("Inventory item is not available in this session party.", 404)

            if not is_gm:
                member = db.exec(
                    select(CampaignMember).where(
                        CampaignMember.campaign_id == session_entry.campaign_id,
                        CampaignMember.user_id == actor_user_id,
                    )
                ).first()
                member_id = getattr(member, "id", None)
                if not member_id or item_entry.member_id != member_id:
                    raise CombatServiceError(
                        "You do not have permission to modify this inventory item.",
                        403,
                    )

            item_name = f"Item {item_entry.id}"
            description = f"{item_name} emite luz mágica."
        else:
            description = raw_description.strip()
            if not description:
                raise CombatServiceError("Luz exige descrição textual não vazia.", 400)
            if len(description) > 300:
                raise CombatServiceError("Descrição de Luz deve ter no máximo 300 caracteres.", 400)

        game_time = get_game_time_seconds(session_id, db)
        attacker_data = cls._as_dict(attacker_model.state_json)
        effects = attacker_data.get("active_spell_effects")
        if not isinstance(effects, list):
            effects = []

        if inventory_item_id is not None:
            filtered_effects = []
            for eff in effects:
                if not isinstance(eff, dict):
                    filtered_effects.append(eff)
                    continue
                metadata = eff.get("metadata")
                if not isinstance(metadata, dict):
                    filtered_effects.append(eff)
                    continue
                if (
                    metadata.get("source_spell_key") == "light"
                    and metadata.get("inventory_item_id") == inventory_item_id
                ):
                    continue
                filtered_effects.append(eff)
            effects = filtered_effects

        effect_id = f"narrative_effect:{uuid4()}"
        effects.append(
            {
                "id": effect_id,
                "kind": "spell_effect",
                "duration_type": "timed",
                "expires_at_participant_id": None,
                "expires_at_game_time_seconds": game_time + 3600,
                "metadata": {
                    "source_spell_key": "light",
                    "source_spell_name": spell_context["spell_name"],
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "inventory_item_id": inventory_item_id,
                    "item_name": item_name,
                    "description": description,
                    "mechanical": False,
                    "narrative": True,
                    "visual": True,
                    "visible_to_all": True,
                    "bright_light_meters": 6,
                    "dim_light_meters": 6,
                    "spell_level": 0,
                },
                "display_label": spell_context["spell_name"],
            }
        )
        attacker_data["active_spell_effects"] = effects
        attacker_model.state_json = finalize_session_state_data(
            attacker_data,
            game_time_seconds=game_time,
        )
        flag_modified(attacker_model, "state_json")
        db.add(attacker_model)

        short = description if len(description) <= 120 else f"{description[:117]}..."
        spell_name = spell_context["spell_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name}: \"{short}\"",
            log_message=f"{attacker['display_name']} conjurou {spell_name}: \"{short}\".",
            extra={
                "created_effect_id": effect_id,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )
