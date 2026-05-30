from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified
from sqlmodel import Session

from app.models.combat import CombatState
from app.services.session_state_finalize import finalize_session_state_data
from ...exceptions import CombatServiceError
from ...host_protocol import CombatServiceHostProtocol


if TYPE_CHECKING:
    _RestorationSpellsBase = CombatServiceHostProtocol
else:
    _RestorationSpellsBase = object


class RestorationSpellsAutomationMixin(_RestorationSpellsBase):
    @classmethod
    async def _cast_lesser_restoration_automation(
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
        from ...condition_effects_predicates import LESSER_RESTORATION_CONDITIONS

        if target_participant is None:
            raise CombatServiceError("Restauração Menor requer um alvo.", 400)

        variant_key = cls._normalize_lookup(getattr(req, "variant_key", None) or "")
        if not variant_key:
            raise CombatServiceError(
                "Especifique o que remover via variant_key "
                "(ex: 'poisoned', 'blinded', 'deafened', 'paralyzed', 'disease').",
                400,
            )
        if variant_key not in LESSER_RESTORATION_CONDITIONS and variant_key != "disease":
            raise CombatServiceError(
                f"lesser_restoration não pode remover '{variant_key}'. "
                f"Valores válidos: {sorted(LESSER_RESTORATION_CONDITIONS | {'disease'})}.",
                400,
            )

        spell_name = spell_context["spell_name"]
        target_name = target_participant["display_name"]

        active = target_participant.get("active_effects") or []
        if variant_key == "disease":
            def _is_removable_disease(e: dict) -> bool:
                if e.get("kind") != "condition":
                    return False
                meta = e.get("metadata") or {}
                return meta.get("removable_by_lesser_restoration") is True or meta.get("disease") is True
            matching = [e for e in active if _is_removable_disease(e)]
            removed_label = "doença"
        else:
            matching = [
                e for e in active
                if e.get("kind") == "condition" and e.get("condition_type") == variant_key
            ]
            removed_label = variant_key

        if not matching:
            raise CombatServiceError(
                f"{target_name} não possui a condição '{removed_label}' para ser removida.",
                400,
            )

        matching_ids = {id(e) for e in matching}
        target_participant["active_effects"] = [e for e in active if id(e) not in matching_ids]
        flag_modified(state, "participants")

        summary_text = f"{spell_name}: condição '{removed_label}' removida de {target_name}."
        log_message = (
            f"{attacker['display_name']} conjurou {spell_name} em {target_name}. "
            f"Condição '{removed_label}' removida."
        )

        return cls._base_spell_result(
            spell_name=spell_name,
            spell_context=spell_context,
            target_display_name=target_name,
            target_kind=target_participant["kind"],
            action_kind="utility",
            summary_text=summary_text,
            log_message=log_message,
            extra={
                "utility": "lesser_restoration",
                "removed_condition": variant_key,
                "removed_count": len(matching),
            },
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
