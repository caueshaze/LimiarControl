from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.game_time import get_game_time_seconds
from app.services.spell_effect_factories import build_warding_bond_effects
from app.services.warding_bond import remove_warding_bonds_involving_participants
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _BondSpellsBase = CombatServiceHostProtocol
else:
    _BondSpellsBase = object


class BondSpellsAutomationMixin(_BondSpellsBase):
    @classmethod
    async def _cast_warding_bond_automation(
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
            raise CombatServiceError("Vínculo de Proteção exige um alvo.", 400)
        if getattr(req, "variant_key", None):
            raise CombatServiceError("Vínculo de Proteção não possui variantes.", 400)
        if target_participant["ref_id"] == attacker["ref_id"]:
            raise CombatServiceError(
                "Vínculo de Proteção deve vincular você a outra criatura voluntária.", 400
            )

        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        # Recast rule: any prior bond involving the caster OR the target ends.
        # Bonds are keyed by ref_id (a player's ref_id is their user id), which
        # keeps in-combat and out-of-combat casts interoperable.
        caster_ref = attacker["ref_id"]
        target_ref = target_participant["ref_id"]
        remove_warding_bonds_involving_participants(state, [caster_ref, target_ref])

        bond_group = str(uuid4())
        target_effect, caster_effect = build_warding_bond_effects(
            cls._build_combat_spell_effect_context(
                spell_key="warding_bond",
                spell_name=spell_name,
                caster_participant_id=attacker["id"],
                target_participant_id=target_participant["id"],
                game_time_seconds=game_time,
                duration_seconds=3600,
                concentration=False,
                concentration_group=None,
                extra_metadata={
                    "bond_group": bond_group,
                    "bond_caster_participant_id": caster_ref,
                    "bond_target_participant_id": target_ref,
                },
            )
        )

        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=target_participant,
            effect=target_effect,
            source_spell_key="warding_bond",
        )
        cls._apply_factory_spell_effect_to_target(
            state=state,
            target_participant=attacker,
            effect=caster_effect,
            source_spell_key="warding_bond",
        )
        flag_modified(state, "participants")

        target_name = target_participant["display_name"]
        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=(
                f"{spell_name}: {target_name} recebe +1 de CA, +1 em salvaguardas e "
                f"resistência a todo dano por até 1 hora. Quando sofrer dano, "
                f"{attacker['display_name']} sofre a mesma quantidade."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em {target_name}, "
                f"criando um vínculo de proteção."
            ),
            extra={
                "utility": "warding_bond",
                "bond_group": bond_group,
                "armor_class_bonus": 1,
                "saving_throw_bonus": 1,
                "grants_resistance_all": True,
                "damage_share_target": "caster",
                "duration_seconds": 3600,
            },
        )
