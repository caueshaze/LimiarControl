from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollActorStats
from app.services.roll_resolution import resolve_attack_base
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol
from ...spell_anchors import (
    create_spell_anchor,
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    move_spell_anchor,
    remove_spell_anchor,
)


def resolve_spiritual_weapon_damage_dice(slot_level: int) -> str:
    num_dice = 1 + max(0, (slot_level - 2) // 2)
    return f"{num_dice}d8"


if TYPE_CHECKING:
    _SpiritualWeaponBase = CombatServiceHostProtocol
else:
    _SpiritualWeaponBase = object


class SpiritualWeaponAutomationMixin(_SpiritualWeaponBase):
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
        if state is None:
            raise CombatServiceError("No combat active for this session", 404)

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
            battle_map: dict[str, object] | None = None
            if state.use_map and state.map_selection:
                battle_map = state.map_selection
            move_spell_anchor(
                state,
                anchor_id=req.anchor_id,
                destination={"x": req.destination["x"], "y": req.destination["y"]},
                max_movement_meters=6.0,
                battle_map=battle_map or {},
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
        cls, state, ref_id: str | None, kind: str | None = None
    ) -> dict | None:
        if ref_id is None:
            return None
        for p in state.participants:
            if p.get("ref_id") == ref_id:
                if kind is None or p.get("kind") == kind:
                    return p
        return None
