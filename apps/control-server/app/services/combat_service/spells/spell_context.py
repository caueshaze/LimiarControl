from __future__ import annotations

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.campaign_entity import CampaignEntity
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.session import Session as CampaignSession
from app.models.session_state import SessionState
from app.services.magic_item_effects import get_magic_item_effect
from app.services.session_state_finalize import finalize_session_state_data

from ..exceptions import CombatServiceError
from .spell_context_resolve import SpellContextResolveMixin


class SpellContextMixin(SpellContextResolveMixin):
    @classmethod
    def _resolve_player_inventory_spell_item(
        cls,
        db: Session,
        session_id: str,
        *,
        player_user_id: str,
        inventory_item_id: str,
    ) -> tuple[InventoryItem, Item, dict]:
        session_entry = db.exec(
            select(CampaignSession).where(CampaignSession.id == session_id)
        ).first()
        if not session_entry:
            raise CombatServiceError("Session not found.", 404)

        member = db.exec(
            select(CampaignMember).where(
                CampaignMember.campaign_id == session_entry.campaign_id,
                CampaignMember.user_id == player_user_id,
            )
        ).first()
        if not member or not member.id:
            raise CombatServiceError("Campaign member not found for this player.", 400)

        inventory_entry = db.exec(
            select(InventoryItem).where(
                InventoryItem.id == inventory_item_id,
                InventoryItem.campaign_id == session_entry.campaign_id,
                InventoryItem.member_id == member.id,
            )
        ).first()
        if not inventory_entry:
            raise CombatServiceError("Magic item not found in the player's inventory.", 404)
        if session_entry.party_id is not None and inventory_entry.party_id not in (None, session_entry.party_id):
            raise CombatServiceError("Magic item is not available in this session party.", 400)

        item = db.exec(
            select(Item).where(
                Item.id == inventory_entry.item_id,
                Item.campaign_id == session_entry.campaign_id,
            )
        ).first()
        if not item:
            raise CombatServiceError("Catalog item for the magic item was not found.", 404)

        effect = get_magic_item_effect(item)
        if not effect or effect.get("type") != "cast_spell":
            raise CombatServiceError("This item cannot cast a spell.", 400)
        return inventory_entry, item, effect

    @classmethod
    def _get_target_hp_snapshot(
        cls,
        db: Session,
        session_id: str,
        target_ref_id: str,
        target_kind: str,
    ) -> tuple[int | None, int | None]:
        target_model, *_ = cls._get_stats(db, target_ref_id, target_kind, session_id)
        if target_kind == "player":
            data = cls._as_dict(target_model.state_json)
            return (
                cls._safe_int(data.get("currentHP"), 0),
                cls._safe_int(data.get("maxHP"), 0),
            )

        npc = db.exec(
            select(CampaignEntity).where(CampaignEntity.id == target_model.campaign_entity_id)
        ).first()
        max_hp = npc.max_hp if npc and npc.max_hp is not None else 0
        current_hp = target_model.current_hp if target_model.current_hp is not None else max_hp
        return current_hp, max_hp

    @classmethod
    def _consume_player_spell_slot(
        cls, attacker_model: SessionState, slot_level: int
    ) -> None:
        data = cls._as_dict(attacker_model.state_json)
        spellcasting = cls._as_dict(data.get("spellcasting"))
        slots = cls._as_dict(spellcasting.get("slots"))
        lvl_key = str(slot_level)
        slot_data = cls._as_dict(slots.get(lvl_key)) or {"used": 0, "max": 0}
        if slot_data.get("used", 0) >= slot_data.get("max", 0):
            raise CombatServiceError("No spell slots of this level remaining")
        slot_data["used"] = cls._safe_int(slot_data.get("used"), 0) + 1
        slots[lvl_key] = slot_data
        spellcasting["slots"] = slots
        data["spellcasting"] = spellcasting
        attacker_model.state_json = finalize_session_state_data(data)
        flag_modified(attacker_model, "state_json")
