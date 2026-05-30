from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_shillelagh_effect
from ...exceptions import CombatServiceError


class BuffsWeaponAutomationMixin:
    @classmethod
    async def _cast_true_strike_automation(
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
        if target_participant is None:
            raise CombatServiceError("Golpe Certeiro exige um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Golpe Certeiro não possui variantes.", 400)

        result = cls._clear_concentration_for_source(
            state, source_participant_id=attacker["id"], db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])

        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        effect = cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=attacker["id"],
            duration_type="until_turn_end",
            expires_at_participant_id=attacker["id"],
            created_at_game_time_seconds=game_time,
            metadata={
                "source_spell_key": "true_strike",
                "source_spell_name": spell_name,
                "concentration": True,
                "concentration_group": concentration_group,
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "target_participant_id": target_participant["id"],
                "target_ref_id": target_participant["ref_id"],
                "target_kind": target_participant["kind"],
                "target_display_name": target_participant["display_name"],
                "mechanical": True,
                "utility": "true_strike",
                "available_from_next_turn": True,
                "declarative_effect": {
                    "type": "roll_advantage_modifier",
                    "params": {
                        "mode": "advantage",
                        "roll_types": ["attack"],
                        "applies_when_attacking_participant_id": target_participant["id"],
                        "consume_on_apply": True,
                        "source": "true_strike",
                    },
                },
            },
            display_label=spell_name,
        )
        cls._append_effect_to_participant(attacker, effect)
        flag_modified(state, "participants")

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name}: {attacker['display_name']} focou nas defesas de "
                f"{target_participant['display_name']}. No próximo turno, o primeiro "
                "ataque contra esse alvo terá Vantagem."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name}, mirando "
                f"{target_participant['display_name']}."
            ),
            extra={
                "utility": "true_strike",
                "target_participant_id": target_participant["id"],
                "target_ref_id": target_participant["ref_id"],
                "concentration_group": concentration_group,
                "grants_advantage": True,
                "available_from_next_turn": True,
                "consume_on_first_eligible_attack": True,
            },
        )

    @classmethod
    def _resolve_shillelagh_weapon(
        cls,
        db: Session,
        session_id: str,
        *,
        attacker: dict,
        weapon_item_id: str,
    ) -> tuple:
        inventory_item, item = cls._resolve_player_weapon_item(
            db,
            session_id,
            attacker.get("ref_id", ""),
            weapon_item_id,
        )
        if not inventory_item.is_equipped:
            raise CombatServiceError(
                "Bordão Místico exige arma equipada/empunhada.",
                400,
            )
        weapon_key = cls._normalize_lookup(
            getattr(item, "canonical_key_snapshot", None)
        ).replace(" ", "_")
        if weapon_key not in {"club", "quarterstaff"}:
            raise CombatServiceError(
                "Bordão Místico só pode afetar porrete (club) ou bordão (quarterstaff).",
                400,
            )
        return inventory_item, item, weapon_key

    @classmethod
    async def _cast_shillelagh_automation(
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
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Bordão Místico não possui variantes.", 400)
        weapon_item_id = (
            req.weapon_item_id.strip()
            if isinstance(getattr(req, "weapon_item_id", None), str)
            and req.weapon_item_id.strip()
            else None
        )
        if not weapon_item_id:
            raise CombatServiceError(
                "weapon_item_id (weaponItemId) é obrigatório para Bordão Místico.",
                400,
            )

        _, weapon_item, weapon_key = cls._resolve_shillelagh_weapon(
            db,
            session_id,
            attacker=attacker,
            weapon_item_id=weapon_item_id,
        )

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)
        effect = build_shillelagh_effect(
            cls._build_combat_spell_effect_context(
                spell_key="shillelagh",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=attacker["id"],
                game_time_seconds=game_time,
                duration_seconds=60,
                concentration=False,
                concentration_group=None,
                extra_metadata={
                    "weapon_item_id": weapon_item_id,
                    "weapon_key": weapon_key,
                    "weapon_canonical_key": weapon_key,
                    "weapon_name": weapon_item.name,
                },
            )
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=attacker,
            effect=effect,
            source_spell_key="shillelagh",
        )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name}: {weapon_item.name} foi imbuído com poder natural."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {weapon_item.name}."
            ),
            extra={
                "utility": "shillelagh",
                "weapon_item_id": weapon_item_id,
                "weapon_key": weapon_key,
                "weapon_name": weapon_item.name,
                "duration_seconds": 60,
                "damage_die_override": "1d8",
                "damage_counts_as_magical": True,
            },
        )
