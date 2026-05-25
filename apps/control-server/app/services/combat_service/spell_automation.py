from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.schemas.roll import RollActorStats
from app.services.goodberry_inventory import (
    build_goodberry_expiration,
    grant_catalog_item_to_player_inventory,
)
from app.services.item_condition_tags import (
    normalize_item_condition_tags,
    remove_item_condition_tag,
)
from app.services.game_time import get_game_time_seconds
from app.services.roll_resolution import resolve_attack_base, resolve_saving_throw
from app.services.session_state_finalize import finalize_session_state_data
from app.models.campaign_member import CampaignMember
from app.models.inventory import InventoryItem
from app.models.session import Session as CampaignSession

from .condition_effects import resolve_attack_advantage, resolve_spell_attack_kind
from .exceptions import CombatServiceError
from .spell_anchors import (
    create_spell_anchor,
    get_spell_anchor_by_id,
    get_spell_anchors_for_owner,
    move_spell_anchor,
    remove_spell_anchor,
    validate_spell_anchor_placement,
)
from sqlmodel import select

logger = logging.getLogger(__name__)

_PRODUCE_FLAME_DURATION_SECONDS = 600
_PRODUCE_FLAME_BRIGHT_LIGHT_METERS = 3
_PRODUCE_FLAME_DIM_LIGHT_METERS = 3
_PRODUCE_FLAME_THROW_RANGE_METERS = 9


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
        "charm_person": SpellAutomationSpec(
            canonical_key="charm_person",
            default_mode="saving_throw",
            requires_effect_payload=False,
            handler_name="_cast_charm_person_automation",
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
        "purify_food_and_drink": SpellAutomationSpec(
            canonical_key="purify_food_and_drink",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_purify_food_and_drink_automation",
        ),
        "chill_touch": SpellAutomationSpec(
            canonical_key="chill_touch",
            default_mode="spell_attack",
            requires_effect_payload=False,
            handler_name="_cast_chill_touch_automation",
        ),
        "true_strike": SpellAutomationSpec(
            canonical_key="true_strike",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_true_strike_automation",
        ),
        "shillelagh": SpellAutomationSpec(
            canonical_key="shillelagh",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_shillelagh_automation",
        ),
        "spiritual_weapon": SpellAutomationSpec(
            canonical_key="spiritual_weapon",
            default_mode="spell_attack",
            requires_effect_payload=True,
            handler_name="_cast_spiritual_weapon_automation",
        ),
        "mage_hand": SpellAutomationSpec(
            canonical_key="mage_hand",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_mage_hand_automation",
        ),
        "minor_illusion": SpellAutomationSpec(
            canonical_key="minor_illusion",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_minor_illusion_automation",
        ),
        "prestidigitation": SpellAutomationSpec(
            canonical_key="prestidigitation",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_prestidigitation_automation",
        ),
        "mending": SpellAutomationSpec(
            canonical_key="mending",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_mending_automation",
        ),
        "light": SpellAutomationSpec(
            canonical_key="light",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_light_automation",
        ),
        "detect_magic": SpellAutomationSpec(
            canonical_key="detect_magic",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_magic_automation",
        ),
        "detect_poison_disease": SpellAutomationSpec(
            canonical_key="detect_poison_disease",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_poison_disease_automation",
        ),
        "detect_evil_and_good": SpellAutomationSpec(
            canonical_key="detect_evil_and_good",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_detect_evil_and_good_automation",
        ),
        "comprehend_languages": SpellAutomationSpec(
            canonical_key="comprehend_languages",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_comprehend_languages_automation",
        ),
        "druidcraft": SpellAutomationSpec(
            canonical_key="druidcraft",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_druidcraft_automation",
        ),
        "thaumaturgy": SpellAutomationSpec(
            canonical_key="thaumaturgy",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_thaumaturgy_automation",
        ),
        "produce_flame": SpellAutomationSpec(
            canonical_key="produce_flame",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_produce_flame_automation",
        ),
        "spare_the_dying": SpellAutomationSpec(
            canonical_key="spare_the_dying",
            default_mode="utility",
            requires_effect_payload=False,
            handler_name="_cast_spare_the_dying_automation",
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
        spell_key = cls._normalize_spell_automation_key(spell_canonical_key)
        if spell_key == "animal_friendship":
            creature_type = cls.resolve_effective_creature_type(
                db,
                session_id,
                target_participant,
            )
            if creature_type != "beast":
                raise CombatServiceError("Animal Friendship can only target beasts.", 400)
        elif spell_key == "spare_the_dying":
            creature_type = cls.resolve_effective_creature_type(
                db,
                session_id,
                target_participant,
            )
            if creature_type in ("undead", "construct"):
                raise CombatServiceError(
                    "Poupar os Moribundos não afeta mortos-vivos ou constructos.",
                    400,
                )

    @classmethod
    def _is_hostile_team_context(cls, attacker: dict, target_participant: dict) -> bool:
        attacker_team = str(attacker.get("team") or "").strip().lower()
        target_team = str(target_participant.get("team") or "").strip().lower()
        if attacker_team in {"players", "allies"}:
            return target_team == "enemies"
        if attacker_team == "enemies":
            return target_team in {"players", "allies"}
        return False

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
            db=db,
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
    async def _cast_charm_person_automation(
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
        is_hostile = cls._is_hostile_team_context(attacker, target_participant)
        advantage_mode = "advantage" if is_hostile else "normal"
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
            advantage_mode=advantage_mode,
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
                    expires_at_game_time_seconds=game_time + 3600,
                    metadata={
                        "source_spell_key": "charm_person",
                        "caster_participant_id": attacker["id"],
                        "charmer_participant_id": attacker["id"],
                        "target_knows_charmed_by_caster": True,
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
    async def _cast_purify_food_and_drink_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("purify_food_and_drink não possui variantes.", status_code=400)

        spell_name = spell_context["spell_name"]

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=(
                f"{spell_name}: alimentos e bebidas não mágicos "
                "em uma esfera de 1,5m foram purificados."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name}, "
                "purificando alimentos e bebidas na área."
            ),
            extra={
                "utility": "purify_food_and_drink",
                "purified_food_and_drink": True,
                "radius_meters": 1.5,
                "instantaneous": True,
            },
        )

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
        state,
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
    ) -> tuple[InventoryItem, Item, str]:
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
        active_effects = attacker.get("active_effects")
        if not isinstance(active_effects, list):
            active_effects = []
            attacker["active_effects"] = active_effects
        attacker["active_effects"] = [
            effect
            for effect in active_effects
            if cls._normalize_lookup(
                (cls._get_effect_metadata(effect) or {}).get("source_spell_key")
            )
            != "shillelagh"
        ]
        effect = cls._build_active_effect(
            kind="spell_effect",
            source_participant_id=attacker["id"],
            duration_type="timed",
            created_at_game_time_seconds=game_time,
            expires_at_game_time_seconds=game_time + 60,
            metadata={
                "source_spell_key": "shillelagh",
                "source_spell_name": spell_name,
                "mechanical": True,
                "utility": "shillelagh",
                "weapon_item_id": weapon_item_id,
                "weapon_key": weapon_key,
                "weapon_name": weapon_item.name,
                "eligible_weapon_keys": ["club", "quarterstaff"],
                "override_attack_ability": "spellcasting",
                "override_damage_ability": "spellcasting",
                "override_damage_die": "1d8",
                "damage_counts_as_magical": True,
                "ends_on_recast": True,
                "ends_on_drop_weapon": True,
            },
            display_label=spell_name,
        )
        cls._append_effect_to_participant(attacker, effect)
        flag_modified(state, "participants")

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

    @classmethod
    async def _cast_chill_touch_automation(
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
            raise CombatServiceError("Toque Necrótico exige um alvo.", 400)

        spell_name = spell_context["spell_name"]
        damage_dice = spell_context.get("effect_dice") or "1d8"
        attack_bonus = cls._safe_int(spell_context.get("attack_bonus"), 0)

        _, target_ac, *_ = cls._get_stats(
            db, target_participant["ref_id"], target_participant["kind"],
            session_id, combat_state=state,
        )
        adv_ctx = resolve_attack_advantage(attacker, target_participant, resolve_spell_attack_kind())
        has_adv = getattr(req, "has_advantage", False) or bool(adv_ctx.advantage_sources)
        has_dis = getattr(req, "has_disadvantage", False) or bool(adv_ctx.disadvantage_sources)
        adv_mode = (
            "advantage" if has_adv and not has_dis
            else "disadvantage" if has_dis and not has_adv
            else "normal"
        )
        roll_result = resolve_attack_base(
            RollActorStats(
                display_name=attacker["display_name"],
                abilities={},
                actor_kind="player",
                actor_ref_id=attacker["ref_id"],
            ),
            advantage_mode=adv_mode,
            bonus_override=attack_bonus,
            target_ac=target_ac or 10,
            roll_source=getattr(req, "roll_source", "system"),
            manual_roll=getattr(req, "manual_roll", None),
            manual_rolls=getattr(req, "manual_rolls", None),
        )
        roll_result.is_gm_roll = is_gm
        if adv_ctx.consumed_effect_ids_on_roll:
            cls._consume_effect_ids(attacker, adv_ctx.consumed_effect_ids_on_roll)
            cls._consume_effect_ids(target_participant, adv_ctx.consumed_effect_ids_on_roll)
        is_hit = bool(roll_result.success)
        is_critical = roll_result.selected_roll == 20
        damage = 0
        new_hp = None

        if is_hit:
            _, raw_damage = cls._resolve_damage_roll(
                damage_dice,
                critical=is_critical,
                roll_source=getattr(req, "roll_source", "system"),
            )
            damage = max(0, raw_damage)
            new_hp, _, *_ = cls._apply_spell_effect(
                db, state,
                target_participant["ref_id"],
                target_participant["kind"],
                "damage",
                damage,
                damage_type="Necrotic",
                is_critical=is_critical,
                attacker_participant_id=attacker.get("id"),
            )
            cls._append_effect_to_participant(
                target_participant,
                cls._build_active_effect(
                    kind="spell_effect",
                    source_participant_id=attacker["id"],
                    duration_type="until_turn_start",
                    expires_at_participant_id=attacker["id"],
                    metadata={
                        "source_spell_key": "chill_touch",
                        "prevent_healing": True,
                    },
                    display_label=spell_name,
                ),
            )
            creature_type = cls.resolve_effective_creature_type(db, session_id, target_participant)
            if creature_type == "undead":
                cls._append_effect_to_participant(
                    target_participant,
                    cls._build_active_effect(
                        kind="spell_effect",
                        source_participant_id=attacker["id"],
                        duration_type="until_turn_start",
                        expires_at_participant_id=attacker["id"],
                        metadata={
                            "source_spell_key": "chill_touch",
                            "declarative_effect": {
                                "type": "roll_disadvantage_modifier",
                                "params": {
                                    "mode": "disadvantage",
                                    "roll_types": ["attack"],
                                    "applies_when_attacking_participant_id": attacker["id"],
                                    "consume_on_apply": False,
                                    "source": "chill_touch",
                                },
                            },
                        },
                        display_label=spell_name,
                    ),
                )
            flag_modified(state, "participants")

        target_name = target_participant["display_name"]
        if is_hit:
            summary = (
                f"{spell_name} acertou {target_name} por {damage} de dano necrótico. "
                "Alvo não pode recuperar PV até o início do próximo turno do conjurador."
            )
            log = (
                f"{attacker['display_name']} conjurou {spell_name} e acertou {target_name}. "
                f"Dano: {damage} necrótico."
            )
        else:
            summary = f"{spell_name} errou {target_name}."
            log = f"{attacker['display_name']} conjurou {spell_name} e errou {target_name}."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="spell_attack",
            summary_text=summary,
            log_message=log,
            extra={
                "is_hit": is_hit,
                "is_critical": is_critical,
                "roll": roll_result.total,
                "roll_result": roll_result,
                "damage": damage,
                "new_hp": new_hp,
                "target_ac": target_ac,
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

    @classmethod
    async def _cast_light_automation(
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
        raw_inventory_item_id = getattr(req, "inventory_item_id", None)
        inventory_item_id = (
            raw_inventory_item_id.strip()
            if isinstance(raw_inventory_item_id, str) and raw_inventory_item_id.strip()
            else None
        )
        raw_description = getattr(req, "description", None)
        has_description = isinstance(raw_description, str)
        if (inventory_item_id is None and not has_description) or (
            inventory_item_id is not None and has_description
        ):
            raise CombatServiceError(
                "Luz exige exatamente um alvo narrativo: inventory_item_id ou description.",
                400,
            )

        description: str | None = None
        item_name: str | None = None

        if inventory_item_id is not None:
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
                    raise CombatServiceError(
                        "You do not have permission to modify this inventory item.",
                        403,
                    )

            item_name = f"Item {item_entry.id}"
            description = f"{item_name} emite luz mágica."
        else:
            description = raw_description.strip()
            if not description:
                raise CombatServiceError("Luz exige descrição textual não vazia.", 400)
            if len(description) > 300:
                raise CombatServiceError("Descrição de Luz deve ter no máximo 300 caracteres.", 400)

        game_time = get_game_time_seconds(session_id, db)
        attacker_data = cls._as_dict(attacker_model.state_json)
        effects = attacker_data.get("active_spell_effects")
        if not isinstance(effects, list):
            effects = []

        if inventory_item_id is not None:
            filtered_effects = []
            for eff in effects:
                if not isinstance(eff, dict):
                    filtered_effects.append(eff)
                    continue
                metadata = eff.get("metadata")
                if not isinstance(metadata, dict):
                    filtered_effects.append(eff)
                    continue
                if (
                    metadata.get("source_spell_key") == "light"
                    and metadata.get("inventory_item_id") == inventory_item_id
                ):
                    continue
                filtered_effects.append(eff)
            effects = filtered_effects

        effect_id = f"narrative_effect:{uuid4()}"
        effects.append(
            {
                "id": effect_id,
                "kind": "spell_effect",
                "duration_type": "timed",
                "expires_at_participant_id": None,
                "expires_at_game_time_seconds": game_time + 3600,
                "metadata": {
                    "source_spell_key": "light",
                    "source_spell_name": spell_context["spell_name"],
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "inventory_item_id": inventory_item_id,
                    "item_name": item_name,
                    "description": description,
                    "mechanical": False,
                    "narrative": True,
                    "visual": True,
                    "visible_to_all": True,
                    "bright_light_meters": 6,
                    "dim_light_meters": 6,
                    "spell_level": 0,
                },
                "display_label": spell_context["spell_name"],
            }
        )
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
    async def _cast_detect_magic_automation(
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
        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(
            session_id, state, result["removed_area_effects"],
        )
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_magic",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_magic",
                    "radius_meters": 9,
                    "can_reveal_aura_with_action": True,
                    "reveals_magic_school": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = f"{spell_name} ativa: presença de magia em até 9m por até 10 minutos."
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos arcanos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_detect_poison_disease_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("detect_poison_disease não possui variantes.", status_code=400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_poison_disease",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_poison_disease",
                    "radius_meters": 9,
                    "detects_poisons": True,
                    "detects_poisonous_creatures": True,
                    "detects_diseases": True,
                    "can_identify_poison_or_disease_with_action": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = f"{spell_name} ativa: detecção de venenos e doenças em até 9m por até 10 minutos."
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_detect_evil_and_good_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError("detect_evil_and_good não possui variantes.", status_code=400)

        result = cls._clear_concentration_for_source(
            state,
            source_participant_id=attacker["id"],
            db=db,
        )
        cls._sync_area_effects_if_changed(session_id, state, result["removed_area_effects"])
        concentration_group = str(uuid4())
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        cls._append_effect_to_participant(
            attacker,
            cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + 600,
                metadata={
                    "concentration": True,
                    "concentration_group": concentration_group,
                    "source_spell_key": "detect_evil_and_good",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": False,
                    "narrative": True,
                    "visible_to_all": True,
                    "utility": "detect_evil_and_good",
                    "radius_meters": 9,
                    "detects_creature_types": [
                        "aberration", "celestial", "elemental",
                        "fey", "fiend", "undead",
                    ],
                    "detects_consecrated_or_desecrated": True,
                    "blocked_by": {
                        "stone_cm": 30,
                        "common_metal_cm": 2.5,
                        "lead_sheet": True,
                        "wood_or_earth_meters": 1,
                    },
                },
                display_label=spell_name,
            ),
        )
        flag_modified(state, "participants")

        summary_text = (
            f"{spell_name} ativa: detecção de criaturas sobrenaturais e locais ou objetos "
            "consagrados/profanados em até 9m por até 10 minutos."
        )
        if result["removed_effects"] or result["removed_area_effects"]:
            summary_text += " A concentração anterior terminou."

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=summary_text,
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} e abriu sentidos em 9m."
            ),
            extra={
                "concentration_group": concentration_group,
            },
        )

    @classmethod
    async def _cast_comprehend_languages_automation(
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
        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            raise CombatServiceError(
                "Compreender Idiomas não possui variantes.",
                400,
            )

        attacker_data = cls._as_dict(attacker_model.state_json)
        existing = attacker_data.get("active_spell_effects") or []
        attacker_data["active_spell_effects"] = [
            e for e in existing
            if not (
                e.get("kind") == "spell_effect"
                and e.get("metadata", {}).get("source_spell_key") == "comprehend_languages"
            )
        ]

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        spell_name = spell_context["spell_name"]
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 3600,
            "metadata": {
                "source_spell_key": "comprehend_languages",
                "source_spell_name": spell_name,
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "utility": "comprehend_languages",
                "spell_level": 1,
                "duration_seconds": 3600,
                "understands_spoken_languages": True,
                "understands_written_languages": True,
                "requires_touch_for_written_text": True,
                "literal_meaning_only": True,
                "deciphers_secret_messages": False,
            },
            "display_label": spell_name,
        }

        attacker_data["active_spell_effects"].append(effect)
        attacker_model.state_json = finalize_session_state_data(
            attacker_data,
            game_time_seconds=game_time,
        )
        flag_modified(attacker_model, "state_json")
        db.add(attacker_model)

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=attacker["display_name"],
            target_kind=attacker["kind"],
            summary_text=f"{spell_name} ativa: compreensão literal de idiomas por 1 hora.",
            log_message=f"{attacker['display_name']} conjurou {spell_name}.",
            extra={
                "created_effect_id": effect_id,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )

    @classmethod
    async def _cast_druidcraft_automation(
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
            raise CombatServiceError("Druidismo exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Druidismo exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição de Druidismo deve ter no máximo 300 caracteres.", 400)

        _ALLOWED_EFFECTS = frozenset({
            "weather_prediction",
            "minor_natural_sensory_effect",
            "plant_bloom",
            "harmless_natural_effect",
            "ignite_or_extinguish_small_flame",
        })
        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            if not isinstance(raw_variant, str) or raw_variant.strip().lower() not in _ALLOWED_EFFECTS:
                raise CombatServiceError(
                    f"Druidismo aceita apenas variantes: {', '.join(sorted(_ALLOWED_EFFECTS))}.",
                    400,
                )
            variant_key = raw_variant.strip().lower()
        else:
            variant_key = "minor_natural_sensory_effect"

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 3600,
            "metadata": {
                "source_spell_key": "druidcraft",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "description": description,
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "freeform": True,
                "spell_level": 0,
                "selected_variant_key": variant_key,
                "allowed_effects": sorted(_ALLOWED_EFFECTS),
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
                "selected_variant_key": variant_key,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )

    _THAUMATURGY_ALLOWED_EFFECTS: frozenset[str] = frozenset({
        "booming_voice",
        "flame_omen",
        "harmless_tremor",
        "instantaneous_sound",
        "open_or_close_unlocked_door",
        "alter_eyes",
    })
    _THAUMATURGY_DEFAULT_EFFECT: str = "booming_voice"

    @classmethod
    async def _cast_thaumaturgy_automation(
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
            raise CombatServiceError("Taumaturgia exige descrição textual.", 400)
        description = raw_description.strip()
        if not description:
            raise CombatServiceError("Taumaturgia exige descrição textual não vazia.", 400)
        if len(description) > 300:
            raise CombatServiceError("Descrição de Taumaturgia deve ter no máximo 300 caracteres.", 400)

        raw_variant = getattr(req, "variant_key", None)
        if raw_variant is not None:
            if not isinstance(raw_variant, str) or raw_variant.strip().lower() not in cls._THAUMATURGY_ALLOWED_EFFECTS:
                raise CombatServiceError(
                    f"Taumaturgia aceita apenas variantes: {', '.join(sorted(cls._THAUMATURGY_ALLOWED_EFFECTS))}.",
                    400,
                )
            variant_key = raw_variant.strip().lower()
        else:
            variant_key = cls._THAUMATURGY_DEFAULT_EFFECT

        game_time = get_game_time_seconds(session_id, db)
        effect_id = f"narrative_effect:{uuid4()}"
        effect = {
            "id": effect_id,
            "kind": "spell_effect",
            "duration_type": "timed",
            "expires_at_participant_id": None,
            "expires_at_game_time_seconds": game_time + 60,
            "metadata": {
                "source_spell_key": "thaumaturgy",
                "source_spell_name": spell_context["spell_name"],
                "owner_participant_id": attacker["id"],
                "created_by_participant_id": attacker["id"],
                "description": description,
                "mechanical": False,
                "narrative": True,
                "visible_to_all": True,
                "freeform": True,
                "spell_level": 0,
                "selected_variant_key": variant_key,
                "utility": "thaumaturgy",
                "allowed_effects": sorted(cls._THAUMATURGY_ALLOWED_EFFECTS),
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
                "selected_variant_key": variant_key,
                "__player_state_ids_to_emit": {attacker["ref_id"]},
            },
        )

    @classmethod
    def _remove_existing_produce_flame_effects(
        cls,
        participant: dict,
    ) -> list[dict]:
        effects = cls._get_participant_effects(participant)
        if not effects:
            return []
        removed: list[dict] = []
        kept: list[dict] = []
        for effect in effects:
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "produce_flame"
            ):
                removed.append(effect)
                continue
            kept.append(effect)
        if removed:
            cls._set_participant_effects(participant, kept)
        return removed

    @classmethod
    def _find_produce_flame_effect(
        cls,
        participant: dict,
    ) -> dict | None:
        for effect in cls._get_participant_effects(participant):
            metadata = cls._get_effect_metadata(effect)
            if (
                effect.get("kind") == "spell_effect"
                and metadata.get("source_spell_key") == "produce_flame"
            ):
                return effect
        return None

    @classmethod
    async def _cast_produce_flame_automation(
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
        spell_mode = cls._normalize_lookup(spell_context.get("spell_mode")).replace(" ", "_")
        spell_name = spell_context["spell_name"]
        game_time = get_game_time_seconds(session_id, db)

        if spell_mode == "utility":
            removed = cls._remove_existing_produce_flame_effects(attacker)
            damage_dice = spell_context.get("damage_preview") or spell_context.get("effect_dice") or "1d8"
            effect = cls._build_active_effect(
                kind="spell_effect",
                source_participant_id=attacker["id"],
                duration_type="timed",
                expires_at_participant_id=None,
                created_at_game_time_seconds=game_time,
                expires_at_game_time_seconds=game_time + _PRODUCE_FLAME_DURATION_SECONDS,
                metadata={
                    "source_spell_key": "produce_flame",
                    "source_spell_name": spell_name,
                    "owner_participant_id": attacker["id"],
                    "created_by_participant_id": attacker["id"],
                    "mechanical": True,
                    "narrative": True,
                    "visual": True,
                    "visible_to_all": True,
                    "utility": "produce_flame",
                    "creates_light": True,
                    "bright_light_meters": _PRODUCE_FLAME_BRIGHT_LIGHT_METERS,
                    "dim_light_meters": _PRODUCE_FLAME_DIM_LIGHT_METERS,
                    "can_throw": True,
                    "throw_range_meters": _PRODUCE_FLAME_THROW_RANGE_METERS,
                    "throw_attack_type": "ranged_spell",
                    "damage_dice": damage_dice,
                    "damage_type": "Fire",
                    "resolved_at_character_level": cls._safe_int(
                        cls._as_dict(attacker_model.state_json).get("level"),
                        cls._safe_int(attacker.get("level"), 1),
                    ),
                },
                display_label=spell_name,
            )
            cls._append_effect_to_participant(attacker, effect)
            flag_modified(state, "participants")
            summary = f"{spell_name}: chama criada na sua mão por 10 minutos."
            if removed:
                summary = f"{spell_name}: chama anterior substituída."
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=attacker["display_name"],
                target_kind=attacker["kind"],
                summary_text=summary,
                log_message=f"{attacker['display_name']} conjurou {spell_name} e criou uma chama na mão.",
                extra={
                    "created_effect_id": effect["id"],
                },
            )

        if spell_mode == "spell_attack":
            active_effect = cls._find_produce_flame_effect(attacker)
            if not isinstance(target_participant, dict):
                raise CombatServiceError("Criar Chamas (arremesso) exige alvo.", 400)
            if active_effect is None:
                raise CombatServiceError(
                    "Criar Chamas não está ativo no conjurador para arremessar.",
                    400,
                )
            metadata = cls._get_effect_metadata(active_effect)
            damage_dice = metadata.get("damage_dice")
            if not isinstance(damage_dice, str) or not damage_dice.strip():
                damage_dice = spell_context.get("effect_dice") or "1d8"
            damage_dice = damage_dice.strip()

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
                bonus_override=cls._safe_int(spell_context.get("attack_bonus"), 0),
                target_ac=target_ac or 10,
                roll_source=getattr(req, "roll_source", "system"),
                manual_roll=getattr(req, "manual_roll", None),
                manual_rolls=getattr(req, "manual_rolls", None),
                has_advantage=bool(getattr(req, "has_advantage", False)),
                has_disadvantage=bool(getattr(req, "has_disadvantage", False)),
            )
            roll_result.is_gm_roll = is_gm
            is_hit = bool(roll_result.success)
            damage = 0
            new_hp = None
            if is_hit:
                _, rolled_damage = cls._resolve_damage_roll(
                    damage_dice,
                    roll_source=getattr(req, "roll_source", "system"),
                    manual_roll=None,
                    manual_rolls=None,
                )
                damage = max(0, rolled_damage)
                new_hp, _, _, _ = cls._apply_spell_effect(
                    db,
                    state,
                    target_participant["ref_id"],
                    target_participant["kind"],
                    "damage",
                    damage,
                    damage_type="Fire",
                    is_critical=roll_result.selected_roll == 20,
                    attacker_participant_id=attacker.get("id"),
                )

            cls._consume_effect_ids(attacker, [active_effect.get("id")])
            flag_modified(state, "participants")

            target_name = target_participant.get("display_name") or target_participant.get("ref_id") or "Alvo"
            if is_hit:
                summary = f"{spell_name}: chama arremessada acertou {target_name} ({damage} de dano de fogo)."
            else:
                summary = f"{spell_name}: chama arremessada errou {target_name}."
            return cls._base_spell_result(
                spell_name=spell_name,
                spell_context=spell_context,
                target_display_name=target_name,
                target_kind=target_participant.get("kind") or "session_entity",
                action_kind="spell_attack",
                summary_text=summary,
                log_message=(
                    f"{attacker['display_name']} arremessou {spell_name} em {target_name}."
                ),
                extra={
                    "is_hit": is_hit,
                    "roll": roll_result.total if roll_result else None,
                    "roll_result": roll_result,
                    "target_ac": target_ac,
                    "damage": damage,
                    "new_hp": new_hp,
                },
            )

        raise CombatServiceError(
            "Criar Chamas suporta apenas os modos utility e spell_attack.",
            400,
        )

    @classmethod
    async def _cast_spare_the_dying_automation(
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
        variant_key = getattr(req, "variant_key", None)
        if variant_key:
            raise CombatServiceError(
                "Poupar os Moribundos não possui variantes.", 400
            )

        if not isinstance(target_participant, dict) or not target_participant:
            raise CombatServiceError(
                "Poupar os Moribundos exige um alvo.", 400
            )

        target_status = target_participant.get("status")
        if target_status == "dead":
            raise CombatServiceError(
                "Poupar os Moribundos não afeta criaturas mortas.", 400
            )

        spell_name = spell_context["spell_name"]
        target_kind = target_participant.get("kind", "session_entity")
        target_ref_id = target_participant["ref_id"]

        if target_kind == "player":
            target_model, *_ = cls._get_stats(
                db, target_ref_id, target_kind, session_id, combat_state=state
            )
            data = cls._as_dict(target_model.state_json)
            current_hp = max(0, cls._safe_int(data.get("currentHP"), 0))
            if current_hp > 0:
                raise CombatServiceError(
                    "Poupar os Moribundos só pode afetar criaturas com 0 HP.", 400
                )

            data["deathSaves"] = {"successes": 3, "failures": 0}
            target_model.state_json = finalize_session_state_data(data)
            cls._sync_participant_status(
                db, state, target_ref_id, target_kind, target_model
            )
            flag_modified(target_model, "state_json")
            db.add(target_model)
            flag_modified(state, "participants")
        else:
            target_model, *_ = cls._get_stats(
                db, target_ref_id, target_kind, session_id, combat_state=state
            )
            current_hp = max(0, target_model.current_hp or 0)
            if current_hp > 0:
                raise CombatServiceError(
                    "Poupar os Moribundos só pode afetar criaturas com 0 HP.", 400
                )

            target_participant["status"] = "stable"
            flag_modified(state, "participants")

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_participant["display_name"],
            target_kind=target_kind,
            action_kind="utility",
            summary_text=(
                f"{target_participant['display_name']} foi estabilizado por {spell_name}."
            ),
            log_message=(
                f"{attacker['display_name']} conjurou {spell_name} em "
                f"{target_participant['display_name']}, estabilizando a criatura."
            ),
            extra={
                "utility": "spare_the_dying",
                "stabilized": True,
                "healing": 0,
                "target_hp_after": 0,
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
