from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import logging
import random
from math import floor
import unicodedata
from uuid import uuid4

logger = logging.getLogger(__name__)

from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.base_item import BaseItemKind
from app.models.campaign import Campaign, SystemType
from app.models.campaign_member import CampaignMember
from app.models.campaign_spell import CampaignSpell
from app.models.combat import CombatPhase, CombatState
from app.models.session import Session as CampaignSession
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.models.campaign_entity import CampaignEntity
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatCastSpellRequest,
    CombatEntityActionRequest,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.schemas.campaign_entity import (
    SKILL_ABILITY_MAP,
    CombatAction,
    ability_modifier as derive_ability_modifier,
    resolve_initiative_bonus as resolve_entity_initiative_bonus,
    resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus,
    resolve_skill_bonus as resolve_entity_skill_bonus,
)
from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.services.centrifugo import centrifugo
from app.services.realtime import (
    build_event,
    campaign_channel,
    event_version,
    session_channel,
)
from app.services.session_state_finalize import calculate_player_armor_class_from_state
from app.schemas.roll import RollActorStats

from .exceptions import CombatServiceError, _parse_dice, _roll_dice_expression
from .condition_effects import is_action_blocked, is_movement_blocked


class CombatCoreMixin:
    _PLAYER_SHIELD_BONUS = 2
    _SAVE_SUCCESS_OUTCOME_VALUES = {"none", "half_damage"}
    _COMBAT_SPELL_ACTION_COSTS = {"action", "bonus_action", "reaction"}

    @classmethod
    def _normalize_lookup(cls, value: object) -> str:
        if isinstance(value, Enum):
            value = value.value
        if not isinstance(value, str):
            return ""
        normalized = unicodedata.normalize("NFD", value.strip().lower())
        normalized = "".join(
            char for char in normalized if unicodedata.category(char) != "Mn"
        )
        normalized = normalized.replace("_", " ").replace("-", " ")
        return " ".join(normalized.split())

    @classmethod
    def _safe_optional_int(cls, value: object) -> int | None:
        return value if isinstance(value, int) else None

    @classmethod
    def _normalize_class_id(cls, value: object) -> str:
        return str(value or "").strip().lower()

    @classmethod
    def _get_player_class_feature_ids(cls, data: dict | None) -> set[str]:
        raw_features = (
            cls._as_dict(data).get("classFeatures") if isinstance(data, dict) else None
        )
        if not isinstance(raw_features, list):
            return set()
        return {
            str(feature.get("id"))
            for feature in raw_features
            if isinstance(feature, dict) and isinstance(feature.get("id"), str)
        }

    @classmethod
    def _get_player_fighting_style(cls, data: dict | None) -> str | None:
        payload = cls._as_dict(data)
        fighting_style = payload.get("fightingStyle")
        if isinstance(fighting_style, str) and fighting_style.strip():
            return fighting_style.strip().lower()

        class_id = cls._normalize_class_id(payload.get("class"))
        level = cls._safe_int(payload.get("level"), 1)
        if class_id == "guardian" and level >= 2:
            return "archery"
        return None

    @classmethod
    def _player_has_colossus_slayer(cls, data: dict | None) -> bool:
        payload = cls._as_dict(data)
        feature_ids = cls._get_player_class_feature_ids(payload)
        if "hunter_colossus_slayer" in feature_ids:
            return True
        class_id = cls._normalize_class_id(payload.get("class"))
        subclass = cls._normalize_class_id(payload.get("subclass"))
        level = cls._safe_int(payload.get("level"), 1)
        return class_id == "guardian" and subclass == "hunter" and level >= 3

    @classmethod
    def _resolve_save_damage_amount(
        cls,
        rolled_amount: int,
        *,
        is_saved: bool,
        save_success_outcome: object,
    ) -> int:
        total = max(0, rolled_amount)
        if not is_saved:
            return total
        if cls._normalize_save_success_outcome(save_success_outcome) == "half_damage":
            return floor(total / 2)
        return 0

    @classmethod
    def _get_player_ability_score(
        cls, data: dict, ability_name: str, default: int = 10
    ) -> int:
        abilities = cls._as_dict(data.get("abilities"))
        value = abilities.get(ability_name)
        return value if isinstance(value, int) else default

    @classmethod
    def calculate_player_armor_class_from_state(cls, data: dict | None) -> int:
        return calculate_player_armor_class_from_state(data)

    @classmethod
    def _get_spell_catalog_entry_for_session(
        cls,
        db: Session,
        session_id: str,
        canonical_key: str,
    ):
        normalized_key = canonical_key.strip().lower()
        if not normalized_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        session_entry = cls._get_session_entry(db, session_id)
        if not session_entry:
            raise CombatServiceError("Session not found", 404)

        campaign_spell = db.exec(
            select(CampaignSpell).where(
                CampaignSpell.campaign_id == session_entry.campaign_id,
                CampaignSpell.is_enabled == True,  # noqa: E712
                func.lower(CampaignSpell.canonical_key) == normalized_key,
            )
        ).first()
        if campaign_spell:
            return campaign_spell

        base_spell = get_base_spell_by_canonical_key(
            db=db,
            system=cls._get_campaign_system_for_session(db, session_id),
            canonical_key=canonical_key,
        )
        if not base_spell:
            raise CombatServiceError(
                "Referenced spellCanonicalKey was not found in the catalog."
            )
        return base_spell

    @classmethod
    def _resolve_player_spell_entry(
        cls,
        data: dict,
        *,
        spell_canonical_key: str | None,
        spell_name: str | None = None,
        campaign_spell_id: str | None = None,
    ) -> dict:
        """Find the player's spell entry from character_sheet.spellcasting.spells[].

        Match priority:
          1. campaignSpellId (stable reference to CampaignSpell) — modern path
          2. canonicalKey — standard path
          3. name — legacy compatibility fallback
        """
        spellcasting = cls._as_dict(data.get("spellcasting"))
        spells = spellcasting.get("spells")
        if not isinstance(spells, list):
            raise CombatServiceError("Player has no spellcasting configured.", 400)

        canonical_lookup = cls._normalize_lookup(spell_canonical_key)
        name_lookup = cls._normalize_lookup(spell_name)
        campaign_id_lookup = cls._normalize_lookup(campaign_spell_id)

        # ── modern path ──────────────────────────────────────────────────────
        # campaignSpellId is the authoritative reference for sheet entries
        # written after the spell reference hardening phase.
        if campaign_id_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("campaignSpellId")) == campaign_id_lookup:
                    return raw_spell

        # ── legacy fallback: canonicalKey ────────────────────────────────────
        # Retained for character sheets created before campaignSpellId was written.
        # Remove once all sheets are migrated.  # legacy compatibility — remove after sheet migration phase
        if canonical_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("canonicalKey")) == canonical_lookup:
                    logger.debug(
                        "character sheet spell resolved via legacy canonicalKey fallback",
                        extra={"canonical_key": spell_canonical_key},
                    )
                    return raw_spell

        # ── legacy fallback: name ─────────────────────────────────────────────
        # Last-resort match kept for the oldest sheets.  # legacy compatibility — remove after sheet migration phase
        effective_name_lookup = name_lookup or canonical_lookup
        if effective_name_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("name")) == effective_name_lookup:
                    logger.debug(
                        "character sheet spell resolved via legacy name fallback",
                        extra={"spell_name": spell_name or spell_canonical_key},
                    )
                    return raw_spell

        raise CombatServiceError("Spell is not available on the player's sheet.", 400)

    @classmethod
    def _build_roll_actor_stats_for_save(
        cls,
        db: Session,
        session_id: str,
        ref_id: str,
        kind: str,
        display_name: str,
    ) -> RollActorStats:
        if kind == "player":
            target_model, _, _, _, prof_bonus, _ = cls._get_stats(
                db, ref_id, kind, session_id
            )
            data = cls._as_dict(target_model.state_json)
            abilities = {
                ability_name: cls._safe_int(value, 10)
                for ability_name, value in cls._as_dict(data.get("abilities")).items()
                if ability_name in cls._ENTITY_ABILITY_ALIASES
            }
            saving_throw_proficiencies = cls._as_dict(
                data.get("savingThrowProficiencies")
            )
            saving_throws: dict[str, int] = {}
            for ability_name in cls._ENTITY_ABILITY_ALIASES:
                if saving_throw_proficiencies.get(ability_name) is True:
                    saving_throws[ability_name] = (
                        cls._ability_modifier(
                            cls._safe_int(abilities.get(ability_name), 10)
                        )
                        + prof_bonus
                    )
            return RollActorStats(
                display_name=display_name,
                abilities=abilities,
                saving_throws=saving_throws or None,
                proficiency_bonus=prof_bonus,
                actor_kind="player",
                actor_ref_id=ref_id,
            )

        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {
            ability_name: cls._get_entity_ability_score(
                cls._as_dict(npc.abilities), overrides, ability_name
            )
            for ability_name in cls._ENTITY_ABILITY_ALIASES
        }
        saving_throws = cls._get_entity_saving_throw_overrides(npc, overrides) or None
        _, _, _, _, prof_bonus, _ = cls._get_stats(db, ref_id, kind, session_id)
        return RollActorStats(
            display_name=display_name,
            abilities=abilities,
            saving_throws=saving_throws,
            proficiency_bonus=prof_bonus,
            actor_kind="session_entity",
            actor_ref_id=ref_id,
        )

    @classmethod
    def _clear_participant_pending_attack(cls, participant: dict | None) -> None:
        if not participant or not isinstance(participant, dict):
            return
        participant.pop("pending_attack", None)

    @classmethod
    def _create_pending_attack(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        pending_attack_id = str(uuid4())
        participant["pending_attack"] = {
            **payload,
            "id": pending_attack_id,
        }
        flag_modified(state, "participants")
        return pending_attack_id

    @classmethod
    def _create_pending_spell_effect(
        cls,
        state: CombatState,
        participant: dict,
        payload: dict,
    ) -> str:
        # Spells reuse the participant-level pending slot so combat state shape stays stable,
        # but the type marker keeps the lifecycle explicit and prevents attack/effect mixups.
        return cls._create_pending_attack(
            state,
            participant,
            {
                **payload,
                "type": "player_spell_effect",
            },
        )

    @classmethod
    def _require_pending_attack(
        cls,
        participant: dict,
        pending_attack_id: str,
        *,
        expected_type: str,
    ) -> dict:
        pending_attack = (
            participant.get("pending_attack") if isinstance(participant, dict) else None
        )
        if not isinstance(pending_attack, dict):
            raise CombatServiceError("No pending damage roll for this actor.", 404)
        if pending_attack.get("id") != pending_attack_id:
            raise CombatServiceError("Pending damage roll not found.", 404)
        if pending_attack.get("type") != expected_type:
            raise CombatServiceError("Pending damage roll type mismatch.", 400)
        return pending_attack

    @classmethod
    def _require_pending_spell_effect(
        cls,
        participant: dict,
        pending_spell_id: str,
    ) -> dict:
        return cls._require_pending_attack(
            participant,
            pending_spell_id,
            expected_type="player_spell_effect",
        )

    @classmethod
    def _resolve_damage_roll(
        cls,
        damage_dice: str,
        *,
        critical: bool = False,
        roll_source: str = "system",
        manual_rolls: list[int] | None = None,
    ) -> tuple[list[int], int]:
        if damage_dice == "unarmed":
            return [], 2 if critical else 1

        count, sides, expression_modifier = _parse_dice(damage_dice)
        if count <= 0 or sides <= 0:
            return [], max(0, expression_modifier)

        effective_count = count * (2 if critical else 1)
        if roll_source == "manual":
            manual_values = manual_rolls or []
            if len(manual_values) != effective_count:
                raise CombatServiceError(
                    f"Manual damage roll requires exactly {effective_count} result(s)."
                )
            for value in manual_values:
                if not isinstance(value, int) or value < 1 or value > sides:
                    raise CombatServiceError(
                        f"Manual damage roll values must be between 1 and {sides}."
                    )
            rolls = manual_values
        else:
            rolls = [random.randint(1, sides) for _ in range(effective_count)]

        return rolls, sum(rolls) + expression_modifier

    @classmethod
    def get_state(cls, db: Session, session_id: str) -> CombatState | None:
        return db.exec(
            select(CombatState).where(CombatState.session_id == session_id)
        ).first()

    @classmethod
    def _require_active(cls, state: CombatState | None):
        if not state:
            raise CombatServiceError("No combat active for this session", 404)
        if state.phase != CombatPhase.active:
            raise CombatServiceError("Combat is not in active phase")

    @classmethod
    def _resolve_actor_participant(
        cls,
        state: CombatState,
        actor_user_id: str,
        is_gm: bool,
        actor_participant_id: str | None = None,
    ) -> dict:
        current_p = cls._get_current_participant(state)

        if actor_participant_id and current_p.get("id") != actor_participant_id:
            raise CombatServiceError(
                "Selected actor is not the active participant", 403
            )

        if is_gm:
            return current_p

        if current_p.get("kind") != "player":
            raise CombatServiceError("It's not a player's turn")

        if current_p.get("actor_user_id") != actor_user_id:
            raise CombatServiceError("Not your turn", 403)

        return current_p

    @classmethod
    def _require_actor_status(
        cls, attacker: dict, allowed_statuses: tuple[str, ...], message: str
    ):
        if attacker.get("status") not in allowed_statuses:
            raise CombatServiceError(message, 403)

    @classmethod
    def _require_action_capable(cls, actor: dict) -> None:
        """Raise CombatServiceError if the actor is incapacitated and cannot take actions."""
        if is_action_blocked(actor):
            raise CombatServiceError(
                "This participant is incapacitated and cannot take actions.", 403
            )

    @classmethod
    def _require_movement_capable(cls, actor: dict) -> None:
        """Raise CombatServiceError if the actor's movement is blocked by a condition."""
        if is_movement_blocked(actor):
            raise CombatServiceError(
                "This participant's movement is blocked by a condition.", 403
            )

    @classmethod
    def _get_stats(cls, db: Session, ref_id: str, kind: str, session_id: str = ""):
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
            ac = cls.calculate_player_armor_class_from_state(data)

            # Wild Shape: override AC and physical ability scores with beast form
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
