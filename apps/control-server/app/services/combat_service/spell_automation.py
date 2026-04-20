from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.models.session_entity import SessionEntity
from app.services.goodberry_inventory import (
    build_goodberry_expiration,
    grant_catalog_item_to_player_inventory,
)
from app.services.roll_resolution import resolve_saving_throw

from .exceptions import CombatServiceError

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
            "action_kind": action_kind,
            "effect_kind": None, "damage": 0, "healing": 0, "damage_type": None,
            "is_critical": False, "is_hit": None, "is_saved": None, "new_hp": None,
            "roll": None, "roll_result": None, "target_ac": None,
            "target_display_name": target_display_name, "target_kind": target_kind,
            "save_ability": None, "save_dc": None, "save_success_outcome": None,
            "effect_dice": None, "effect_bonus": None, "pending_spell_id": None,
            "effect_roll_required": False, "summary_text": summary_text,
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
        removed = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
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
        if removed:
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

        if not is_saved:
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="condition",
                    condition_type="charmed",
                    source_participant_id=attacker["id"],
                    duration_type="manual",
                    expires_at_participant_id=target_participant["id"],
                    metadata={
                        "source_spell_key": "animal_friendship",
                        "charmer_participant_id": attacker["id"],
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
