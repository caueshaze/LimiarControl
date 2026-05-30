from __future__ import annotations

from math import floor

from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity import CombatAction

from .condition_effects_predicates import resolve_armor_class_floor
from .exceptions import CombatServiceError
from .host_protocol import CombatServiceHostProtocol


class CombatStatLookupMixin(CombatServiceHostProtocol):

    @classmethod
    def _get_stats(
        cls,
        db: Session,
        ref_id: str,
        kind: str,
        session_id: str = "",
        *,
        combat_state=None,
    ):
        if kind == "player":
            target = (
                db.exec(
                    select(SessionState).where(
                        SessionState.player_user_id == ref_id,
                        SessionState.session_id == session_id,
                    )
                ).first()
                if session_id
                else db.exec(
                    select(SessionState).where(SessionState.player_user_id == ref_id)
                ).first()
            )
            if not target:
                raise CombatServiceError("Player not found")
            data = cls._as_dict(target.state_json)
            abilities = cls._as_dict(data.get("abilities"))
            spellcasting = cls._as_dict(data.get("spellcasting"))
            str_val = abilities.get("strength", 10)
            dex_val = abilities.get("dexterity", 10)
            combat_effects = None
            participant = None
            if combat_state is not None:
                participant = next(
                    (
                        entry
                        for entry in combat_state.participants
                        if entry.get("kind") == "player" and entry.get("ref_id") == ref_id
                    ),
                    None,
                )
                effects = participant.get("active_effects") if isinstance(participant, dict) else None
                combat_effects = effects if isinstance(effects, list) else None
            ac = cls.calculate_player_armor_class_from_state(
                data,
                active_effects=combat_effects,
            )
            if isinstance(participant, dict):
                ac_floor = resolve_armor_class_floor(participant)
                if isinstance(ac_floor, int):
                    ac = max(ac, ac_floor)

            wild_shape = cls._as_dict(data.get("wildShape"))
            if wild_shape.get("active"):
                from app.services.wild_shape_catalog import get_form

                form_key = wild_shape.get("formKey")
                form = get_form(form_key) if isinstance(form_key, str) else None
                if form is not None:
                    ac = form.armor_class
                    str_val = form.str_score
                    dex_val = form.dex_score

            level = data.get("level", 1)
            prof_bonus = floor((level - 1) / 4) + 2
            spell_ability = spellcasting.get("ability")
            spell_mod = spellcasting.get("modifier")
            if not isinstance(spell_mod, int) and isinstance(spell_ability, str):
                spell_score = abilities.get(spell_ability, 10)
                spell_mod = floor((spell_score - 10) / 2)
            if not isinstance(spell_mod, int):
                spell_mod = 0
            return target, ac, str_val, dex_val, prof_bonus, spell_mod
        else:
            target = db.exec(
                select(SessionEntity).where(SessionEntity.id == ref_id)
            ).first()
            if not target:
                raise CombatServiceError("Entity not found")
            npc = db.exec(
                select(CampaignEntity).where(
                    CampaignEntity.id == target.campaign_entity_id
                )
            ).first()
            if not npc:
                raise CombatServiceError("Campaign entity not found")
            abilities = cls._as_dict(npc.abilities)
            overrides = cls._as_dict(target.overrides)
            spellcasting = cls._get_entity_spellcasting(npc, overrides)

            str_val = cls._get_entity_ability_score(abilities, overrides, "strength")
            dex_val = cls._get_entity_ability_score(abilities, overrides, "dexterity")
            ac = cls._get_entity_armor_class(npc, overrides)
            if combat_state is not None:
                participant = next(
                    (
                        entry
                        for entry in combat_state.participants
                        if entry.get("kind") != "player" and entry.get("ref_id") == ref_id
                    ),
                    None,
                )
                if isinstance(participant, dict):
                    ac_floor = resolve_armor_class_floor(participant)
                    if isinstance(ac_floor, int):
                        ac = max(ac, ac_floor)
            spell_ability = (
                cls._normalize_ability_name(spellcasting.get("ability"))
                or "intelligence"
            )
            spell_mod = cls._ability_modifier(
                cls._get_entity_ability_score(abilities, overrides, spell_ability)
            )
            explicit_spell_attack_bonus = spellcasting.get("attackBonus")
            explicit_spell_save_dc = spellcasting.get("saveDc")
            prof_bonus = 2
            if isinstance(explicit_spell_attack_bonus, int):
                prof_bonus = max(0, explicit_spell_attack_bonus - spell_mod)
            elif isinstance(explicit_spell_save_dc, int):
                prof_bonus = max(0, explicit_spell_save_dc - 8 - spell_mod)
            return target, ac, str_val, dex_val, prof_bonus, spell_mod

    @classmethod
    def _get_session_entity_and_campaign_entity(
        cls,
        db: Session,
        session_entity_id: str,
    ) -> tuple[SessionEntity, CampaignEntity]:
        target = db.exec(
            select(SessionEntity).where(SessionEntity.id == session_entity_id)
        ).first()
        if not target:
            raise CombatServiceError("Entity not found")
        npc = db.exec(
            select(CampaignEntity).where(CampaignEntity.id == target.campaign_entity_id)
        ).first()
        if not npc:
            raise CombatServiceError("Campaign entity not found")
        return target, npc

    @classmethod
    def _get_combat_action_for_entity(
        cls,
        db: Session,
        session_entity_id: str,
        combat_action_id: str,
    ) -> tuple[SessionEntity, CampaignEntity, CombatAction]:
        target, npc = cls._get_session_entity_and_campaign_entity(db, session_entity_id)
        raw_actions = npc.combat_actions if isinstance(npc.combat_actions, list) else []
        raw_action = next(
            (
                entry
                for entry in raw_actions
                if isinstance(entry, dict) and entry.get("id") == combat_action_id
            ),
            None,
        )
        if not raw_action:
            raise CombatServiceError("Combat action not found", 404)
        try:
            action = CombatAction(**raw_action)
        except Exception as exc:
            raise CombatServiceError(
                f"Invalid combat action definition: {exc}", 400
            ) from exc
        return target, npc, action
