from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.models.session_entity import SessionEntity
from app.schemas.roll import RollActorStats
from app.services.goodberry_inventory import (
    build_goodberry_expiration,
    grant_catalog_item_to_player_inventory,
)
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw

from .exceptions import CombatServiceError
from .spell_anchors import (
    create_spell_anchor,
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    move_spell_anchor,
    remove_spell_anchor,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SpellAutomationSpec:
    canonical_key: str
    default_mode: str
    requires_effect_payload: bool
    handler_name: str


class CombatSpellAutomationMixin:
    _SPELL_AUTOMATION_REGISTRY: dict[str, SpellAutomationSpec] = {
        "animal_friendship": SpellAutomationSpec(
            canonical_key="animal_friendship",
            default_mode="saving_throw",
            requires_effect_payload=False,
            handler_name="_cast_animal_friendship_automation",
        ),
        "hunters_mark": SpellAutomationSpec(
            canonical_key="hunters_mark",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_hunters_mark_automation",
        ),
        "goodberry": SpellAutomationSpec(
            canonical_key="goodberry",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_goodberry_automation",
        ),
        "spiritual_weapon": SpellAutomationSpec(
            canonical_key="spiritual_weapon",
            default_mode="spell_attack",
            requires_effect_payload=True,
            handler_name="_cast_spiritual_weapon_automation",
        ),
    }

    @classmethod
    def _normalize_spell_automation_key(cls, value: object) -> str:
        return cls._normalize_lookup(value).replace(" ", "_")

    @classmethod
    def _get_spell_automation_spec(
        cls, canonical_key: object
    ) -> SpellAutomationSpec | None:
        return cls._SPELL_AUTOMATION_REGISTRY.get(
            cls._normalize_spell_automation_key(canonical_key)
        )

    @classmethod
    def _spell_requires_effect_payload(cls, canonical_key: object) -> bool:
        spec = cls._get_spell_automation_spec(canonical_key)
        if spec is None:
            return True
        return spec.requires_effect_payload

    @classmethod
    def _spell_default_mode_override(cls, canonical_key: object) -> str | None:
        spec = cls._get_spell_automation_spec(canonical_key)
        if spec is None:
            return None
        return spec.default_mode

    @classmethod
    def _validate_spell_automation_target(
        cls,
        db: Session,
        session_id: str,
        *,
        spell_canonical_key: str,
        target_participant: dict,
    ) -> None:
        if cls._normalize_spell_automation_key(spell_canonical_key) != "animal_friendship":
            return
        if target_participant.get("kind") != "session_entity":
            raise CombatServiceError("Animal Friendship can only target beasts.", 400)
        session_entity = db.exec(
            select(SessionEntity).where(SessionEntity.id == target_participant["ref_id"])
        ).first()
        if not session_entity:
            raise CombatServiceError("Target entity not found.", 404)
        creature = db.exec(
            select(CampaignEntity).where(
                CampaignEntity.id == session_entity.campaign_entity_id
            )
        ).first()
        creature_type = cls._normalize_lookup(getattr(creature, "creature_type", None))
        if creature_type != "beast":
            raise CombatServiceError("Animal Friendship can only target beasts.", 400)

    @staticmethod
    def _base_spell_result(
        *,
        spell_name: str,
        spell_context: dict,
        target_display_name: str,
        target_kind: str,
        action_kind: str = "utility",
        summary_text: str = "",
        log_message: str = "",
        inventory_refresh_required: bool = False,
        extra: dict | None = None,
    ) -> dict:
        result: dict = {
            "spell_name": spell_name,
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "selected_variant_key": spell_context.get("selected_variant_key"),
            "selected_variant_label": spell_context.get("selected_variant_label"),
            "context_origin": spell_context.get("context_origin") or "initial_cast",
            "concentration_group": spell_context.get("concentration_group"),
            "action_kind": action_kind,
            "effect_kind": None, "damage": 0, "healing": 0, "damage_type": None,
            "is_critical": False, "is_hit": None, "is_saved": None, "new_hp": None,
            "roll": None, "roll_result": None, "target_ac": None,
            "target_display_name": target_display_name, "target_kind": target_kind,
            "save_ability": None, "save_dc": None, "save_success_outcome": None,
            "effect_dice": None, "effect_bonus": None, "pending_spell_id": None,
            "effect_roll_required": False, "summary_text": summary_text,
            "applied_declarative_effects_by_target": None,
            "inventory_refresh_required": inventory_refresh_required,
            "__log_message": log_message, "__player_state_ids_to_emit": set(),
            "__entity_hp_update_target": None, "__entity_previous_hp": None,
        }
        if extra:
            result.update(extra)
        return result

    @classmethod
    async def _cast_spell_via_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict | None:
        spec = cls._get_spell_automation_spec(spell_context.get("spell_canonical_key"))
        if spec is None:
            return None
        handler = getattr(cls, spec.handler_name, None)
        if handler is None:
            return None
        logger.info(
            "[spell:automation] spell=%s pipeline=special_handler handler=%s session=%s actor=%s",
            spell_context.get("spell_canonical_key"),
            spec.handler_name,
            session_id,
            attacker.get("ref_id"),
        )
        return await handler(
            db,
            session_id,
            attacker=attacker,
            attacker_model=attacker_model,
            actor_user_id=actor_user_id,
            is_gm=is_gm,
            req=req,
            state=state,
            spell_context=spell_context,
            target_participant=target_participant,
        )

    @classmethod
    async def _cast_hunters_mark_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict:
        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
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
    async def _cast_animal_friendship_automation(
        cls, db: Session, session_id: str, *, attacker: dict, attacker_model,
        actor_user_id: str, is_gm: bool, req, state: CombatState,
        spell_context: dict, target_participant: dict,
    ) -> dict:
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_participant["ref_id"],
                target_participant["kind"],
                target_participant["display_name"],
            ),
            ability=spell_context["save_ability"],
            dc=cls._safe_int(spell_context.get("save_dc"), 0),
        )
        roll_result.is_gm_roll = is_gm
        roll_total = roll_result.total
        is_saved = bool(roll_result.success)

        game_time = get_game_time_seconds(session_id, db)
        if not is_saved:
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="condition",
                    condition_type="charmed",
                    source_participant_id=attacker["id"],
                    duration_type="timed",
                    created_at_game_time_seconds=game_time,
                    expires_at_game_time_seconds=game_time + 86400,
                    metadata={
                        "source_spell_key": "animal_friendship",
                        "caster_participant_id": attacker["id"],
                        "charmer_participant_id": attacker["id"],
                        "termination_conditions": [
                            {"type": "target_takes_damage_from_caster_or_allies"},
                        ],
                    },
                ),
            )
            flag_modified(state, "participants")

        spell_name = spell_context["spell_name"]
        if is_saved:
            summary_text = f"{target_participant['display_name']} passou na salvaguarda contra {spell_name}."
        else:
            summary_text = f"{target_participant['display_name']} falhou na salvaguarda e ficou enfeitiçado."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            action_kind="saving_throw",
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} lançou {spell_name} em {target_participant['display_name']}: "
                f"{'o alvo passou na salvaguarda' if is_saved else 'o alvo falhou e ficou enfeitiçado'}."
            ),
            extra={
                "is_saved": is_saved,
                "roll": roll_total,
                "roll_result": roll_result,
                "save_ability": spell_context.get("save_ability"),
                "save_dc": spell_context.get("save_dc"),
                "save_success_outcome": spell_context.get("save_success_outcome"),
            },
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
    async def _cast_spiritual_weapon_automation(
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
        # Remove existing anchor if recasting (recast substitutes, not stacks)
        for old_anchor in get_spell_anchors_for_owner(state, attacker["id"]):
            if old_anchor.get("source_spell_key") == "spiritual_weapon":
                remove_spell_anchor(state, old_anchor["id"])

        anchor_cell = getattr(req, "anchor_cell", None)
        if not anchor_cell:
            raise CombatServiceError("Posição da Arma Espiritual é obrigatória.", 400)

        slot_level = cls._safe_int(spell_context.get("slot_level"), 2)
        damage_dice = resolve_spiritual_weapon_damage_dice(slot_level)
        spell_mod = cls._safe_int(spell_context.get("spell_mod"), 0)
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)
        anchor_position = {"x": anchor_cell.x, "y": anchor_cell.y}

        create_spell_anchor(
            state,
            anchor={
                "source_spell_key": "spiritual_weapon",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "position": anchor_position,
                "duration_type": "rounds",
                "remaining_rounds": 10,
                "expires_on": "turn_start",
                "expires_at_participant_id": attacker["id"],
                "render_kind": "spiritual_weapon",
                "movement": {"max_meters_per_follow_up": 6.0},
                "metadata": {
                    "damage_dice": damage_dice,
                    "spell_mod": spell_mod,
                    "attack_bonus": attack_bonus,
                    "slot_level": slot_level,
                },
            },
        )
        flag_modified(state, "spell_anchors")

        spell_name = spell_context["spell_name"]
        is_hit = None
        damage = 0
        roll_result = None

        if target_participant:
            _, target_ac, *_ = cls._get_stats(
                db,
                target_participant["ref_id"],
                target_participant["kind"],
                session_id,
                combat_state=state,
            )
            roll_result = resolve_attack_base(
                RollActorStats(
                    display_name=attacker["display_name"],
                    abilities={},
                    actor_kind="player",
                    actor_ref_id=attacker["ref_id"],
                ),
                bonus_override=attack_bonus,
                target_ac=target_ac or 10,
                roll_source="system",
            )
            roll_result.is_gm_roll = is_gm
            is_hit = bool(roll_result.success)
            if is_hit:
                _, raw = cls._resolve_damage_roll(damage_dice, roll_source="system")
                damage = max(0, raw + spell_mod)
                cls._apply_spell_effect(
                    db,
                    state,
                    target_participant["ref_id"],
                    target_participant["kind"],
                    "damage",
                    damage,
                    damage_type="force",
                    is_critical=roll_result.selected_roll == 20,
                    attacker_participant_id=attacker.get("id"),
                )

        target_name = target_participant["display_name"] if target_participant else None
        if not target_participant:
            summary = f"Arma Espiritual criada em ({anchor_position['x']}, {anchor_position['y']})."
            log = f"{attacker['display_name']} conjurou {spell_name}."
        elif is_hit:
            summary = f"Arma Espiritual acertou {target_name} por {damage} de dano de força."
            log = f"{attacker['display_name']} conjurou {spell_name} e acertou {target_name}. Dano: {damage} de força."
        else:
            summary = f"Arma Espiritual errou {target_name}. A arma permanece ativa."
            log = f"{attacker['display_name']} conjurou {spell_name} e errou {target_name}."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name or attacker["display_name"],
            target_kind=target_participant["kind"] if target_participant else "player",
            action_kind="spell_attack" if target_participant else "utility",
            summary_text=summary,
            log_message=log,
            extra={
                "is_hit": is_hit,
                "roll": roll_result.total if roll_result else None,
                "roll_result": roll_result,
                "damage": damage,
            },
        )


    @classmethod
    async def use_spiritual_weapon_action(
        cls,
        db: Session,
        session_id: str,
        req,
        actor_user_id: str,
        is_gm: bool = False,
    ) -> dict:
        if not req.destination and not req.target_ref_id:
            raise CombatServiceError(
                "Informe um destino ou um alvo para a Arma Espiritual.", 400
            )

        state = cls.get_state(db, session_id)
        cls._require_active(state)

        attacker = cls._find_participant_by_id(state, req.actor_participant_id)
        if not attacker:
            raise CombatServiceError("Participante não encontrado.", 404)
        if not is_gm and attacker.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("Você só pode controlar seu próprio personagem.", 403)
        cls._require_actor_status(attacker, ("active",), "Apenas participantes ativos podem usar a Arma Espiritual.")
        cls._consume_turn_resource(attacker, "bonus_action", is_gm=is_gm)

        anchor = get_spell_anchor_by_id(state, req.anchor_id)
        if not anchor:
            raise CombatServiceError("Arma Espiritual não encontrada.", 404)
        if anchor.get("source_spell_key") != "spiritual_weapon":
            raise CombatServiceError("O efeito informado não é uma Arma Espiritual.", 400)
        if anchor.get("owner_participant_id") != attacker["id"]:
            raise CombatServiceError("Esta Arma Espiritual pertence a outro conjurador.", 403)

        metadata = anchor.get("metadata") or {}
        attack_bonus = cls._safe_int(metadata.get("attack_bonus"), 0)
        damage_dice = metadata.get("damage_dice", "1d8")
        spell_mod = cls._safe_int(metadata.get("spell_mod"), 0)

        if req.destination:
            battle_map = None
            if state.use_map and state.map_selection:
                battle_map = state.map_selection
            move_spell_anchor(
                state,
                anchor_id=req.anchor_id,
                destination={"x": req.destination["x"], "y": req.destination["y"]},
                max_movement_meters=6.0,
                battle_map=battle_map,
            )
            anchor = get_spell_anchor_by_id(state, req.anchor_id) or anchor
            flag_modified(state, "spell_anchors")

        is_hit = None
        damage = 0
        roll_result = None
        target_p = None

        if req.target_ref_id:
            target_p = cls._find_participant_by_ref_id(state, req.target_ref_id, req.target_kind)
            if not target_p:
                raise CombatServiceError("Alvo não encontrado no combate.", 404)
            _, target_ac, *_ = cls._get_stats(
                db,
                target_p["ref_id"],
                target_p["kind"],
                session_id,
                combat_state=state,
            )
            roll_result = resolve_attack_base(
                RollActorStats(
                    display_name=attacker["display_name"],
                    abilities={},
                    actor_kind="player",
                    actor_ref_id=attacker["ref_id"],
                ),
                bonus_override=attack_bonus,
                target_ac=target_ac or 10,
                roll_source="system",
                manual_roll=getattr(req, "manual_roll", None),
            )
            roll_result.is_gm_roll = is_gm
            is_hit = bool(roll_result.success)
            if is_hit:
                _, raw = cls._resolve_damage_roll(damage_dice, roll_source="system")
                damage = max(0, raw + spell_mod)
                cls._apply_spell_effect(
                    db,
                    state,
                    target_p["ref_id"],
                    target_p["kind"],
                    "damage",
                    damage,
                    damage_type="force",
                    is_critical=roll_result.selected_roll == 20,
                    attacker_participant_id=attacker.get("id"),
                )

        flag_modified(state, "participants")
        db.add(state)
        db.commit()
        db.refresh(state)

        await cls._emit_state(session_id, state)

        target_name = target_p["display_name"] if target_p else None
        if not target_p:
            log_message = f"{attacker['display_name']} moveu a Arma Espiritual."
        elif is_hit:
            log_message = f"Arma Espiritual de {attacker['display_name']} acertou {target_name}. Dano: {damage} de força."
        else:
            log_message = f"Arma Espiritual de {attacker['display_name']} errou {target_name}."

        await cls._emit_log(session_id, {"message": log_message, "source": "spiritual_weapon_action"})

        return {
            "isHit": is_hit,
            "roll": roll_result.total if roll_result else None,
            "damage": damage,
            "targetDisplayName": target_name,
            "logMessage": log_message,
        }

    @classmethod
    def _find_participant_by_ref_id(
        cls, state, ref_id: str, kind: str | None = None
    ) -> dict | None:
        for p in state.participants:
            if p.get("ref_id") == ref_id:
                if kind is None or p.get("kind") == kind:
                    return p
        return None


def resolve_spiritual_weapon_damage_dice(slot_level: int) -> str:
    """Return damage dice for Spiritual Weapon at the given slot level.

    Slot 2 → 1d8, slot 4 → 2d8, slot 6 → 3d8, slot 8 → 4d8.
    """
    num_dice = 1 + max(0, (slot_level - 2) // 2)
    return f"{num_dice}d8"
