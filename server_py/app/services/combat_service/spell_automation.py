from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session, select

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatState
from app.models.session_entity import SessionEntity
from app.schemas.roll import RollResult
from app.services.goodberry_inventory import (
    build_goodberry_expiration,
    grant_catalog_item_to_player_inventory,
)
from app.services.roll_resolution import resolve_saving_throw

from .exceptions import CombatServiceError


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
        "magic_missile": SpellAutomationSpec(
            canonical_key="magic_missile",
            default_mode="direct_damage",
            requires_effect_payload=False,
            handler_name="",
        ),
    }

    @classmethod
    def _normalize_spell_automation_key(cls, value: object) -> str:
        return cls._normalize_lookup(value).replace(" ", "_")

    @classmethod
    def _get_spell_automation_spec(cls, canonical_key: object) -> SpellAutomationSpec | None:
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
    def _get_effect_metadata(cls, effect: dict | None) -> dict:
        metadata = cls._as_dict(effect).get("metadata") if isinstance(effect, dict) else None
        return metadata if isinstance(metadata, dict) else {}

    @classmethod
    def _find_participant_by_id(cls, state: CombatState, participant_id: str | None) -> dict | None:
        if not participant_id:
            return None
        return next(
            (participant for participant in state.participants if participant.get("id") == participant_id),
            None,
        )

    @classmethod
    def _build_active_effect(
        cls,
        *,
        kind: str,
        source_participant_id: str | None,
        condition_type: str | None = None,
        numeric_value: int | None = None,
        duration_type: str = "manual",
        remaining_rounds: int | None = None,
        expires_at_participant_id: str | None = None,
        metadata: dict | None = None,
        display_label: str | None = None,
    ) -> dict:
        expires_on = None
        if duration_type == "until_turn_start":
            expires_on = "turn_start"
        elif duration_type == "until_turn_end":
            expires_on = "turn_end"
        elif duration_type == "rounds":
            expires_on = "turn_start"

        return {
            "id": str(uuid4()),
            "source_participant_id": source_participant_id,
            "kind": kind,
            "condition_type": condition_type if kind == "condition" else None,
            "numeric_value": numeric_value,
            "duration_type": duration_type,
            "remaining_rounds": remaining_rounds,
            "expires_on": expires_on,
            "expires_at_participant_id": expires_at_participant_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or None,
            "display_label": display_label,
        }

    @classmethod
    def _append_effect_to_participant(cls, participant: dict, effect: dict) -> None:
        effects = cls._get_participant_effects(participant)
        effects.append(effect)
        cls._set_participant_effects(participant, effects)

    @classmethod
    def _remove_effect_group(
        cls,
        state: CombatState,
        *,
        concentration_group: str,
    ) -> list[dict]:
        removed: list[dict] = []
        for participant in state.participants:
            effects = cls._get_participant_effects(participant)
            if not effects:
                continue
            kept: list[dict] = []
            for effect in effects:
                metadata = cls._get_effect_metadata(effect)
                if metadata.get("concentration_group") == concentration_group:
                    removed.append(
                        {
                            **effect,
                            "target_participant_id": participant.get("id"),
                            "target_display_name": participant.get("display_name", ""),
                        }
                    )
                    continue
                kept.append(effect)
            cls._set_participant_effects(participant, kept)
        return removed

    @classmethod
    def _clear_concentration_for_source(
        cls,
        state: CombatState,
        *,
        source_participant_id: str,
    ) -> list[dict]:
        groups: set[str] = set()
        for participant in state.participants:
            for effect in cls._get_participant_effects(participant):
                metadata = cls._get_effect_metadata(effect)
                if (
                    effect.get("source_participant_id") == source_participant_id
                    and metadata.get("concentration") is True
                    and isinstance(metadata.get("concentration_group"), str)
                ):
                    groups.add(metadata["concentration_group"])

        removed: list[dict] = []
        for group_id in groups:
            removed.extend(cls._remove_effect_group(state, concentration_group=group_id))
        return removed

    @classmethod
    def _clear_concentration_for_participant_status(
        cls,
        state: CombatState | None,
        *,
        source_participant_id: str | None,
    ) -> list[dict]:
        if not state or not source_participant_id:
            return []
        removed = cls._clear_concentration_for_source(
            state,
            source_participant_id=source_participant_id,
        )
        if removed:
            flag_modified(state, "participants")
        return removed

    @classmethod
    def _get_hunters_mark_effect_for_target(
        cls,
        participant: dict,
        *,
        target_participant_id: str,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "hunters_mark"
                and metadata.get("marked_target_participant_id") == target_participant_id
            ):
                return effect
        return None

    @classmethod
    def _get_charmed_effect_against_target(
        cls,
        participant: dict,
        *,
        target_participant_id: str,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "condition"
                and effect.get("condition_type") == "charmed"
                and metadata.get("charmer_participant_id") == target_participant_id
            ):
                return effect
        return None

    @classmethod
    def _assert_hostile_action_allowed(
        cls,
        attacker: dict,
        target: dict | None,
        *,
        action_label: str,
    ) -> None:
        if not target or not isinstance(target.get("id"), str):
            return
        blocked_effect = cls._get_charmed_effect_against_target(
            attacker,
            target_participant_id=target["id"],
        )
        if blocked_effect is None:
            return
        raise CombatServiceError(
            f"You cannot use {action_label} against {target['display_name']} while charmed.",
            400,
        )

    @classmethod
    def _get_concentration_group_ids(cls, participant: dict | None) -> list[str]:
        if not isinstance(participant, dict):
            return []

        groups: list[str] = []
        seen: set[str] = set()
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if metadata.get("concentration") is not True:
                continue
            group_id = metadata.get("concentration_group")
            if not isinstance(group_id, str) or not group_id or group_id in seen:
                continue
            seen.add(group_id)
            groups.append(group_id)
        return groups

    @classmethod
    def _resolve_concentration_check_after_damage(
        cls,
        db: Session,
        session_id: str,
        *,
        state: CombatState | None,
        target_participant: dict | None,
        target_ref_id: str,
        target_kind: str,
        damage_taken: int,
        roll_source: str = "system",
        manual_roll: int | None = None,
    ) -> dict | None:
        if state is None or not isinstance(target_participant, dict) or damage_taken <= 0:
            return None

        concentration_groups = cls._get_concentration_group_ids(target_participant)
        if not concentration_groups:
            return None

        dc = max(10, damage_taken // 2)
        roll_result = resolve_saving_throw(
            cls._build_roll_actor_stats_for_save(
                db,
                session_id,
                target_ref_id,
                target_kind,
                target_participant.get("display_name") or "Target",
            ),
            ability="constitution",
            dc=dc,
            roll_source=roll_source,
            manual_roll=manual_roll,
        )
        roll_result.roll_source = roll_source
        succeeded = bool(roll_result.success)

        broken_effect_labels: list[str] = []
        source_spell_keys: set[str] = set()
        if not succeeded:
            removed = cls._clear_concentration_for_source(
                state,
                source_participant_id=target_participant.get("id", ""),
            )
            if removed:
                flag_modified(state, "participants")
            for effect in removed:
                label = effect.get("display_label")
                if not isinstance(label, str) or not label.strip():
                    label = cls._effect_label(effect)
                if label and label not in broken_effect_labels:
                    broken_effect_labels.append(label)
                metadata = cls._get_effect_metadata(effect)
                spell_key = metadata.get("source_spell_key")
                if isinstance(spell_key, str) and spell_key.strip():
                    source_spell_keys.add(spell_key)

        if succeeded:
            summary_text = (
                f"{target_participant['display_name']} manteve a concentração "
                f"({roll_result.total} no save de CON contra CD {dc})."
            )
        else:
            broken_text = (
                f" Efeitos encerrados: {', '.join(broken_effect_labels)}."
                if broken_effect_labels
                else ""
            )
            summary_text = (
                f"{target_participant['display_name']} perdeu a concentração "
                f"({roll_result.total} no save de CON contra CD {dc}).{broken_text}"
            )

        return {
            "actor_participant_id": target_participant.get("id"),
            "actor_display_name": target_participant.get("display_name") or "Target",
            "damage_taken": damage_taken,
            "dc": dc,
            "success": succeeded,
            "roll_result": roll_result,
            "broken_effect_labels": broken_effect_labels,
            "source_spell_keys": sorted(source_spell_keys),
            "summary_text": summary_text,
        }

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
            select(CampaignEntity).where(CampaignEntity.id == session_entity.campaign_entity_id)
        ).first()
        creature_type = cls._normalize_lookup(getattr(creature, "creature_type", None))
        if creature_type != "beast":
            raise CombatServiceError("Animal Friendship can only target beasts.", 400)

    @classmethod
    async def _cast_spell_via_automation(
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
        target_participant: dict,
    ) -> dict | None:
        spec = cls._get_spell_automation_spec(spell_context.get("spell_canonical_key"))
        if spec is None:
            return None
        handler = getattr(cls, spec.handler_name, None)
        if handler is None:
            return None
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
        target_participant: dict,
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

        return {
            "spell_name": spell_name,
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "utility",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": target_participant["display_name"],
            "target_kind": target_participant["kind"],
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": None,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "summary_text": summary_text,
            "inventory_refresh_required": False,
            "__log_message": (
                f"{attacker['display_name']} conjurou {spell_name} em {target_participant['display_name']}. "
                f"A marca está ativa."
            ),
            "__player_state_ids_to_emit": set(),
            "__entity_hp_update_target": None,
            "__entity_previous_hp": None,
        }

    @classmethod
    async def _cast_animal_friendship_automation(
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
        target_participant: dict,
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
            summary_text = (
                f"{target_participant['display_name']} passou na salvaguarda contra {spell_name}."
            )
        else:
            summary_text = (
                f"{target_participant['display_name']} falhou na salvaguarda e ficou enfeitiçado."
            )

        return {
            "spell_name": spell_name,
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "saving_throw",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": is_saved,
            "new_hp": None,
            "roll": roll_total,
            "roll_result": roll_result,
            "target_ac": None,
            "target_display_name": target_participant["display_name"],
            "target_kind": target_participant["kind"],
            "save_ability": spell_context.get("save_ability"),
            "save_dc": spell_context.get("save_dc"),
            "save_success_outcome": spell_context.get("save_success_outcome"),
            "effect_dice": None,
            "effect_bonus": None,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "summary_text": summary_text,
            "inventory_refresh_required": False,
            "__log_message": (
                f"{attacker['display_name']} lançou {spell_name} em {target_participant['display_name']}: "
                f"{'o alvo passou na salvaguarda' if is_saved else 'o alvo falhou e ficou enfeitiçado'}."
            ),
            "__player_state_ids_to_emit": set(),
            "__entity_hp_update_target": None,
            "__entity_previous_hp": None,
        }

    @classmethod
    async def _cast_goodberry_automation(
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
        target_participant: dict,
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

        return {
            "spell_name": spell_name,
            "spell_canonical_key": spell_context["spell_canonical_key"],
            "action_kind": "utility",
            "effect_kind": None,
            "damage": 0,
            "healing": 0,
            "damage_type": None,
            "is_critical": False,
            "is_hit": None,
            "is_saved": None,
            "new_hp": None,
            "roll": None,
            "roll_result": None,
            "target_ac": None,
            "target_display_name": attacker["display_name"],
            "target_kind": "player",
            "save_ability": None,
            "save_dc": None,
            "save_success_outcome": None,
            "effect_dice": None,
            "effect_bonus": None,
            "pending_spell_id": None,
            "effect_roll_required": False,
            "summary_text": "10 Bom Fruto foram adicionados ao seu inventário.",
            "inventory_refresh_required": True,
            "__log_message": (
                f"{attacker['display_name']} conjurou {spell_name} e criou 10 Bom Fruto."
            ),
            "__player_state_ids_to_emit": set(),
            "__entity_hp_update_target": None,
            "__entity_previous_hp": None,
            "__inventory_item_id": getattr(inventory_entry, "id", None),
        }
