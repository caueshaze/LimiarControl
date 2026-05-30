from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_member import CampaignMember
from app.models.combat import CombatState
from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession
from app.services.game_time import get_game_time_seconds
from app.services.item_condition_tags import (
    normalize_item_condition_tags,
    remove_item_condition_tag,
)
from app.services.session_state_finalize import finalize_session_state_data
from ...exceptions import CombatServiceError
from ...spell_anchors import (
    create_spell_anchor,
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    move_spell_anchor,
    remove_spell_anchor,
    validate_spell_anchor_placement,
)

logger = logging.getLogger(__name__)


def _to_inventory_read_dict(entry: InventoryItem) -> dict:
    try:
        condition_tags = normalize_item_condition_tags(entry.condition_tags)
    except ValueError:
        condition_tags = []
    condition_tag_labels = [
        {"tag": tag, "label": "Quebrado" if tag == "broken" else tag}
        for tag in condition_tags
    ]
    return {
        "id": entry.id,
        "campaignId": entry.campaign_id,
        "partyId": entry.party_id,
        "memberId": entry.member_id,
        "itemId": entry.item_id,
        "quantity": entry.quantity,
        "chargesCurrent": entry.charges_current,
        "isEquipped": entry.is_equipped,
        "notes": entry.notes,
        "conditionTags": condition_tags,
        "conditionTagLabels": condition_tag_labels,
        "sourceSpellCanonicalKey": entry.source_spell_canonical_key,
        "expiresAt": entry.expires_at,
        "createdAt": entry.created_at,
        "updatedAt": entry.updated_at,
    }


class CantripAnchorsAutomationMixin:
    @classmethod
    async def _cast_mage_hand_automation(
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
        for old_anchor in get_spell_anchors_for_owner(state, attacker["id"]):
            if old_anchor.get("source_spell_key") == "mage_hand":
                remove_spell_anchor(state, old_anchor["id"])

        anchor_cell = getattr(req, "anchor_cell", None)
        if not anchor_cell:
            raise CombatServiceError("Posição da Mãos Mágicas é obrigatória.", 400)

        anchor_position = {"x": anchor_cell.x, "y": anchor_cell.y}
        caster_position = attacker.get("position")
        if not isinstance(caster_position, dict):
            raise CombatServiceError("Conjurador sem posição válida no mapa.", 400)

        battle_map = None
        if state.use_map and state.map_selection:
            battle_map = state.map_selection
        if not isinstance(battle_map, dict):
            raise CombatServiceError("Mapa de combate é obrigatório para Mãos Mágicas.", 400)

        validate_spell_anchor_placement(
            caster_position={"x": int(caster_position.get("x", 0)), "y": int(caster_position.get("y", 0))},
            target_position=anchor_position,
            range_meters=9.0,
            requires_point_sight=False,
            requires_point_effect=False,
            battle_map=battle_map,
        )

        create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "mage_hand",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "position": anchor_position,
                "duration_type": "rounds",
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": attacker["id"],
                "render_kind": "mage_hand",
                "movement": {"max_meters_per_follow_up": 9.0},
                "metadata": {},
            },
        )
        flag_modified(state, "spell_anchors")

        spell_name = spell_context["spell_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name} criada em ({anchor_position['x']}, {anchor_position['y']}).",
            log_message=f"{attacker['display_name']} conjurou {spell_name}.",
        )

    @classmethod
    async def use_mage_hand_action(
        cls,
        db: Session,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool = False,
    ) -> dict:
        if not req.destination:
            raise CombatServiceError("Informe um destino para Mãos Mágicas.", 400)

        state = cls.get_state(db, session_id)
        cls._require_active(state)

        attacker = cls._find_participant_by_id(state, req.actor_participant_id)
        if not attacker:
            raise CombatServiceError("Participante não encontrado.", 404)
        if not is_gm and attacker.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("Você só pode controlar seu próprio personagem.", 403)
        cls._require_actor_status(attacker, ("active",), "Apenas participantes ativos podem usar Mãos Mágicas.")

        anchor = get_spell_anchor_by_id(state, req.anchor_id)
        if not anchor:
            raise CombatServiceError("Mãos Mágicas não encontrada.", 404)
        if anchor.get("source_spell_key") != "mage_hand":
            raise CombatServiceError("O efeito informado não é uma Mãos Mágicas.", 400)
        if anchor.get("owner_participant_id") != attacker["id"]:
            raise CombatServiceError("Esta Mãos Mágicas pertence a outro conjurador.", 403)

        battle_map = state.map_selection if state.use_map and state.map_selection else None
        move_spell_anchor(
            state,
            anchor_id=req.anchor_id,
            destination={"x": req.destination["x"], "y": req.destination["y"]},
            max_movement_meters=9.0,
            battle_map=battle_map,
        )
        anchor = get_spell_anchor_by_id(state, req.anchor_id) or anchor
        flag_modified(state, "spell_anchors")
        db.add(state)
        db.commit()
        db.refresh(state)

        await cls._emit_state(session_id, state)
        log_message = (
            f"{attacker['display_name']} moveu Mãos Mágicas para "
            f"({anchor['position']['x']}, {anchor['position']['y']})."
        )
        await cls._emit_log(session_id, {"message": log_message, "source": "mage_hand_action"})
        return {"position": anchor["position"], "logMessage": log_message}

    @classmethod
    async def _cast_minor_illusion_automation(
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
        for old_anchor in get_spell_anchors_for_owner(state, attacker["id"]):
            if old_anchor.get("source_spell_key") == "minor_illusion":
                remove_spell_anchor(state, old_anchor["id"])

        anchor_cell = getattr(req, "anchor_cell", None)
        if not anchor_cell:
            raise CombatServiceError("Posição da Ilusão Menor é obrigatória.", 400)
        raw_variant = getattr(req, "variant_key", None)
        if not isinstance(raw_variant, str):
            raise CombatServiceError("Ilusão Menor exige variante 'sound' ou 'image'.", 400)
        variant = raw_variant.strip()
        if variant not in {"sound", "image"}:
            raise CombatServiceError("Ilusão Menor aceita apenas variantes 'sound' ou 'image'.", 400)

        raw_description = getattr(req, "description", None)
        if not isinstance(raw_description, str):
            raise CombatServiceError("Ilusão Menor exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Ilusão Menor exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição da Ilusão Menor deve ter no máximo 300 caracteres.", 400)

        anchor_position = {"x": anchor_cell.x, "y": anchor_cell.y}
        caster_position = attacker.get("position")
        if not isinstance(caster_position, dict):
            raise CombatServiceError("Conjurador sem posição válida no mapa.", 400)
        battle_map = state.map_selection if state.use_map and state.map_selection else None
        if not isinstance(battle_map, dict):
            raise CombatServiceError("Mapa de combate é obrigatório para Ilusão Menor.", 400)

        validate_spell_anchor_placement(
            caster_position={"x": int(caster_position.get("x", 0)), "y": int(caster_position.get("y", 0))},
            target_position=anchor_position,
            range_meters=9.0,
            requires_point_sight=False,
            requires_point_effect=False,
            battle_map=battle_map,
        )

        create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "minor_illusion",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "position": anchor_position,
                "duration_type": "rounds",
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": attacker["id"],
                "render_kind": "minor_illusion",
                "metadata": {
                    "illusion_kind": variant,
                    "description": description,
                    "blocks_movement": False,
                    "blocks_los": False,
                    "blocks_loe": False,
                },
            },
        )
        flag_modified(state, "spell_anchors")

        short = description if len(description) <= 80 else f"{description[:77]}..."
        spell_name = spell_context["spell_name"]
        kind_pt = "som" if variant == "sound" else "imagem"
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=(
                f"{spell_name} ({kind_pt}) criada em ({anchor_position['x']}, {anchor_position['y']}): "
                f"\"{short}\""
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} ({kind_pt}): \"{short}\"."
            ),
            extra={"selected_variant_key": variant},
        )

    @classmethod
    async def _cast_prestidigitation_automation(
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
        raw_description = getattr(req, "description", None)
        if not isinstance(raw_description, str):
            raise CombatServiceError("Prestidigitação exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Prestidigitação exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição de Prestidigitação deve ter no máximo 300 caracteres.", 400)

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 3600,
            "metadata": {
                "source_spell_key": "prestidigitation",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "description": description,
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "freeform": True,
                "spell_level": 0,
                "selected_variant_key": getattr(req, "variant_key", None),
            },
            "display_label": spell_context["spell_name"],
        }

        attacker_data = cls._as_dict(attacker_model.state_json)
        effects = attacker_data.get("active_spell_effects")
        if not isinstance(effects, list):
            effects = []
        effects.append(effect)
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

    @classmethod
    async def _cast_mending_automation(
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
        inventory_item_id = None
        raw_inventory_item_id = getattr(req, "inventory_item_id", None)
        if isinstance(raw_inventory_item_id, str) and raw_inventory_item_id.strip():
            inventory_item_id = raw_inventory_item_id.strip()
        elif isinstance(spell_context.get("inventory_item_id"), str) and spell_context.get("inventory_item_id").strip():
            inventory_item_id = spell_context.get("inventory_item_id").strip()
        if not inventory_item_id:
            raise CombatServiceError("Mending exige inventory_item_id.", 400)

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
                raise CombatServiceError("You do not have permission to modify this inventory item.", 403)

        current_tags = normalize_item_condition_tags(item_entry.condition_tags)
        next_tags, changed = remove_item_condition_tag(current_tags, "broken")
        item_entry.condition_tags = normalize_item_condition_tags(next_tags)
        db.add(item_entry)

        removed_tags = ["broken"] if changed else []
        spell_name = spell_context["spell_name"]
        inventory_read = _to_inventory_read_dict(item_entry)
        summary = (
            f"{spell_name}: item reparado."
            if changed
            else f"{spell_name}: nada para reparar."
        )
        log_message = (
            f"{attacker['display_name']} conjurou {spell_name} e removeu 'broken' do item {item_entry.id}."
            if changed
            else f"{attacker['display_name']} conjurou {spell_name}, mas o item {item_entry.id} não estava quebrado."
        )
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary,
            log_message=log_message,
            extra={
                "changed": changed,
                "removed_tags": removed_tags,
                "removedTags": removed_tags,
                "inventory_item": inventory_read,
                "inventoryItem": inventory_read,
                "inventory_refresh_required": True,
            },
        )
