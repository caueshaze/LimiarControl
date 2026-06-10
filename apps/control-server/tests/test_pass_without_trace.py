from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.models.combat import CombatPhase, CombatState
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.combat import CombatService
from app.services.ooc_spell_cast_service import (
    cast_spell_out_of_combat_for_player as _cast_spell_out_of_combat_for_player,
)


def _participant(
    participant_id: str,
    ref_id: str,
    *,
    kind: str = "player",
    name: str | None = None,
    actor_user_id: str | None = None,
    status: str = "active",
    team: str | None = None,
) -> dict:
    resolved_team = team or ("players" if kind == "player" else "enemies")
    return {
        "id": participant_id,
        "ref_id": ref_id,
        "kind": kind,
        "display_name": name or participant_id,
        "status": status,
        "team": resolved_team,
        "visible": True,
        "actor_user_id": actor_user_id,
        "active_effects": [],
        "turn_resources": {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
        },
    }


def _combat_state(participants: list[dict]) -> CombatState:
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
        local_distances={},
        use_map=False,
    )


def _roll_result(*, total: int, modifier_used: int = 2, roll_type: str = "skill", ability: str | None = None, skill: str | None = None):
    return SimpleNamespace(
        total=total,
        modifier_used=modifier_used,
        formula=f"1d20 + {modifier_used}",
        dc=15,
        success=False,
        check_modifier_sources=[],
        ability=ability,
        skill=skill,
        roll_type=roll_type,
    )


class PassWithoutTraceCombatTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.caster = _participant("caster-1", "player-1", actor_user_id="user-1", name="Ranger")
        self.ally = _participant("ally-1", "player-2", actor_user_id="user-2", name="Cleric", team="players")
        self.enemy = _participant("enemy-1", "enemy-1", kind="session_entity", name="Goblin")
        self.far = _participant("enemy-2", "enemy-2", kind="session_entity", name="Bandit")
        self.dead = _participant("dead-1", "dead-1", kind="session_entity", name="Corpse", status="dead")
        self.state = _combat_state([self.caster, self.ally, self.enemy, self.far, self.dead])
        self.state.local_distances = {
            "player-1": {
                "player-2": 6.0,
                "enemy-1": 9.0,
                "enemy-2": 12.0,
            }
        }

    def _spell_context(self) -> dict:
        return {
            "spell_name": "Pass Without Trace",
            "spell_canonical_key": "pass_without_trace",
            "spell_mode": "utility",
            "effect_kind": None,
            "effect_timing": "persistent",
            "selection_type": "multi_creature",
            "target_anchor": "selected_targets",
            "range_kind": "distance",
            "attack_type": "none",
            "save_ability": None,
            "save_dc": None,
            "concentration": True,
        }

    def _req(self, target_ref_ids: list[str] | None = None) -> SimpleNamespace:
        return SimpleNamespace(
            variant_key=None,
            target_ref_ids=target_ref_ids,
            target_ref_id=None,
            target_variant_assignments=None,
            effect_instance_targets=None,
            override_resource_limit=False,
        )

    async def test_registry_and_cast_apply_real_effects(self) -> None:
        spec = CombatService._get_spell_automation_spec("pass_without_trace")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.handler_name, "_cast_pass_without_trace_automation")

        result = await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2", "enemy-2", "dead-1"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        caster_roles = [
            (effect.get("metadata") or {}).get("effect_role")
            for effect in self.caster["active_effects"]
        ]
        self.assertIn("concentration_marker", caster_roles)
        self.assertIn("skill_check_bonus", caster_roles)
        self.assertNotIn("next_weapon_hit_rider", caster_roles)
        self.assertEqual(result["damage"], 0)
        self.assertIsNone(result["save_dc"])
        self.assertNotIn("area_shape", (CombatService.UTILITY_SPELL_CONTEXT_META["pass_without_trace"]))
        self.assertNotIn("reactiveBurst", (CombatService.UTILITY_SPELL_CONTEXT_META["pass_without_trace"]))
        self.assertEqual(set(result["affected_participant_ids"]), {"caster-1", "ally-1"})
        rejected = {entry["target_ref_id"]: entry["reason"] for entry in result["rejected_targets"]}
        self.assertEqual(rejected["enemy-2"], "out_of_range")
        self.assertEqual(rejected["dead-1"], "invalid_status")

    async def test_missing_distance_rejects_specific_target_and_caster_is_always_included(self) -> None:
        self.state.local_distances = {"player-1": {}}
        result = await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        self.assertEqual(result["affected_participant_ids"], ["caster-1"])
        self.assertEqual(result["rejected_targets"][0]["reason"], "missing_distance")

    async def test_stealth_bonus_applies_only_to_selected_targets_and_only_for_stealth(self) -> None:
        await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        with patch.object(CombatService, "get_state", return_value=self.state):
            stealth_roll = _roll_result(total=9, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=stealth_roll,
                roll_type="skill",
            )
            self.assertEqual(stealth_roll.total, 19)
            self.assertEqual(stealth_roll.modifier_used, 12)
            self.assertEqual(stealth_roll.check_modifier_sources[0]["modifier_type"], "skill_flat_bonus")

            acrobatics_roll = _roll_result(total=9, ability="dexterity", skill="acrobatics")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=acrobatics_roll,
                roll_type="skill",
            )
            self.assertEqual(acrobatics_roll.total, 9)

            ability_roll = _roll_result(total=9, roll_type="ability", ability="dexterity")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=ability_roll,
                roll_type="ability",
            )
            self.assertEqual(ability_roll.total, 9)

            save_roll = _roll_result(total=9, roll_type="save", ability="dexterity")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=save_roll,
                roll_type="save",
            )
            self.assertEqual(save_roll.total, 9)

            unaffected_roll = _roll_result(total=9, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="session_entity",
                actor_ref_id="enemy-2",
                roll_result=unaffected_roll,
                roll_type="skill",
            )
            self.assertEqual(unaffected_roll.total, 9)

    async def test_distance_checked_at_roll_time(self) -> None:
        await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )
        self.state.local_distances["player-1"]["player-2"] = 12.0

        with patch.object(CombatService, "get_state", return_value=self.state):
            stealth_roll = _roll_result(total=9, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=stealth_roll,
                roll_type="skill",
            )
            self.assertEqual(stealth_roll.total, 9)

    async def test_caster_moves_far_away_and_selected_ally_loses_stealth_bonus(self) -> None:
        await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )
        self.state.local_distances["player-1"]["player-2"] = 15.0

        with patch.object(CombatService, "get_state", return_value=self.state):
            stealth_roll = _roll_result(total=11, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=stealth_roll,
                roll_type="skill",
            )
            self.assertEqual(stealth_roll.total, 11)

    async def test_selected_target_that_becomes_dead_or_removed_gets_no_bonus(self) -> None:
        await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )
        self.ally["status"] = "dead"

        with patch.object(CombatService, "get_state", return_value=self.state):
            stealth_roll = _roll_result(total=10, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=stealth_roll,
                roll_type="skill",
            )
            self.assertEqual(stealth_roll.total, 10)

        self.ally["status"] = "removed"
        with patch.object(CombatService, "get_state", return_value=self.state):
            removed_roll = _roll_result(total=10, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=removed_roll,
                roll_type="skill",
            )
            self.assertEqual(removed_roll.total, 10)

    async def test_generic_dexterity_check_without_stealth_gets_no_bonus(self) -> None:
        await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        with patch.object(CombatService, "get_state", return_value=self.state):
            dex_ability_roll = _roll_result(total=12, roll_type="ability", ability="dexterity")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=dex_ability_roll,
                roll_type="ability",
            )
            self.assertEqual(dex_ability_roll.total, 12)

    async def test_duplicate_pass_without_trace_instances_do_not_stack_beyond_ten(self) -> None:
        self.ally["active_effects"] = [
            {
                "id": "pwt-1",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "pass_without_trace",
                    "source_spell_name": "Pass Without Trace",
                    "effect_role": "skill_check_bonus",
                    "concentration": True,
                    "concentration_group": "grp-a",
                    "origin_caster_ref_id": "player-1",
                    "skill": "stealth",
                    "ability": "dexterity",
                    "bonus_value": 10,
                    "bonus_applies_to": "dexterity_stealth_checks",
                },
            },
            {
                "id": "pwt-2",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "pass_without_trace",
                    "source_spell_name": "Pass Without Trace",
                    "effect_role": "skill_check_bonus",
                    "concentration": True,
                    "concentration_group": "grp-b",
                    "origin_caster_ref_id": "player-3",
                    "skill": "stealth",
                    "ability": "dexterity",
                    "bonus_value": 10,
                    "bonus_applies_to": "dexterity_stealth_checks",
                },
            },
        ]
        self.state.participants.append(
            {
                **_participant("other-caster", "player-3", actor_user_id="user-3", name="Druid"),
                "active_effects": [
                    {
                        "id": "marker-a",
                        "kind": "spell_effect",
                        "metadata": {"concentration": True, "concentration_group": "grp-a"},
                    },
                    {
                        "id": "marker-b",
                        "kind": "spell_effect",
                        "metadata": {"concentration": True, "concentration_group": "grp-b"},
                    },
                ],
            }
        )

        with patch.object(CombatService, "get_state", return_value=self.state):
            stealth_roll = _roll_result(total=9, ability="dexterity", skill="stealth")
            CombatService._apply_roll_dice_modifiers_for_actor(
                MagicMock(),
                "session-1",
                actor_kind="player",
                actor_ref_id="player-2",
                roll_result=stealth_roll,
                roll_type="skill",
            )
            self.assertEqual(stealth_roll.total, 19)

    async def test_trace_metadata_and_concentration_cleanup(self) -> None:
        result = await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )
        self.assertEqual(result["trace_suppression"]["exception"], "magical_tracking")
        ally_effect = next(
            effect for effect in self.ally["active_effects"]
            if (effect.get("metadata") or {}).get("source_spell_key") == "pass_without_trace"
        )
        metadata = ally_effect["metadata"]
        self.assertTrue(metadata["suppresses_tracks"])
        self.assertTrue(metadata["prevents_nonmagical_tracking"])
        self.assertEqual(metadata["tracking_exception"], "magical_tracking")

        clear_result = CombatService._clear_concentration_for_source(
            self.state,
            source_participant_id=self.caster["id"],
            db=MagicMock(),
        )
        self.assertTrue(clear_result["removed_effects"])
        self.assertEqual(self.ally["active_effects"], [])
        self.assertEqual(self.caster["active_effects"], [])

    async def test_recast_and_other_concentration_remove_previous_group(self) -> None:
        first = await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req(["player-2"]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )
        second = await CombatService._cast_pass_without_trace_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=self._req([]),
            state=self.state,
            spell_context=self._spell_context(),
            target_participant=None,
        )

        first_group = first["concentration_group"]
        second_group = second["concentration_group"]
        self.assertNotEqual(first_group, second_group)
        self.assertFalse(any((effect.get("metadata") or {}).get("concentration_group") == first_group for effect in self.caster["active_effects"]))
        self.assertFalse(any((effect.get("metadata") or {}).get("concentration_group") == first_group for effect in self.ally["active_effects"]))

        hail_context = {
            "spell_name": "Hail of Thorns",
            "spell_canonical_key": "hail_of_thorns",
            "spell_mode": "utility",
            "effect_kind": "damage",
            "effect_timing": "triggered",
            "selection_type": "none",
            "target_anchor": "trigger_target",
            "range_kind": "self",
            "attack_type": "none",
            "save_ability": "dexterity",
            "save_dc": 14,
            "concentration": True,
            "effect_dice": "1d10",
        }
        await CombatService._cast_hail_of_thorns_automation(
            MagicMock(),
            "session-1",
            attacker=self.caster,
            attacker_model=MagicMock(),
            actor_user_id="user-1",
            is_gm=False,
            req=SimpleNamespace(variant_key=None),
            state=self.state,
            spell_context=hail_context,
            target_participant=None,
        )
        self.assertFalse(any((effect.get("metadata") or {}).get("source_spell_key") == "pass_without_trace" for effect in self.caster["active_effects"]))


class PassWithoutTraceOocTests(unittest.IsolatedAsyncioTestCase):
    def _campaign_spell(self) -> MagicMock:
        spell = MagicMock()
        spell.canonical_key = "pass_without_trace"
        spell.name_pt = "Passar sem Rastros"
        spell.name_en = "Pass without Trace"
        spell.level = 2
        spell.concentration = True
        spell.out_of_combat_castable = True
        spell.out_of_combat_target = "multi_ally"
        spell.effects_json = []
        spell.variants_json = []
        return spell

    def _caster_state(self) -> MagicMock:
        state = MagicMock()
        state.state_json = {
            "spellcasting": {
                "saveDc": 14,
                "slots": {"2": {"used": 0, "max": 2}},
                "spells": [
                    {
                        "id": "spell-pwt-1",
                        "canonicalKey": "pass_without_trace",
                        "level": 2,
                        "prepared": True,
                    }
                ],
            }
        }
        state.id = "ss-caster"
        state.session_id = "session-1"
        state.player_user_id = "user-1"
        return state

    async def test_ooc_self_cast_persists_real_effects_and_modifies_stealth(self) -> None:
        caster_state = self._caster_state()
        campaign_spell = self._campaign_spell()
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        db = MagicMock()
        exec_results = [caster_state, campaign_spell]

        def exec_side_effect(*_args, **_kwargs):
            result = MagicMock()
            value = exec_results.pop(0) if exec_results else None
            result.first.return_value = value
            result.all.return_value = []
            return result

        db.exec.side_effect = exec_side_effect
        req = OutOfCombatCastRequest(spellId="spell-pwt-1", slotLevel=2)
        actor_user = MagicMock(id="user-1")

        await _cast_spell_out_of_combat_for_player(
            entry=entry,
            session_id="session-1",
            req=req,
            actor_user=actor_user,
            caster_user_id="user-1",
            session=db,
            cast_by_gm=False,
            ensure_session_state=MagicMock(return_value=caster_state),
            finalize_session_state_data=lambda data, **_kwargs: data,
            publish_state_update=AsyncMock(),
            to_state_read=MagicMock(return_value=caster_state),
        )

        effects = caster_state.state_json.get("active_spell_effects", [])
        self.assertEqual(len(effects), 2)
        pwt_effect = next(
            effect for effect in effects
            if (effect.get("metadata") or {}).get("effect_role") == "skill_check_bonus"
        )
        self.assertTrue(pwt_effect["metadata"]["suppresses_tracks"])
        self.assertTrue(pwt_effect["metadata"]["prevents_nonmagical_tracking"])

        roll_result = _roll_result(total=9, ability="dexterity", skill="stealth")
        db_for_roll = MagicMock()
        session_state_result = MagicMock()
        session_state_result.first.return_value = caster_state
        db_for_roll.exec.return_value = session_state_result
        with patch.object(CombatService, "get_state", return_value=None):
            CombatService._apply_roll_dice_modifiers_for_actor(
                db_for_roll,
                "session-1",
                actor_kind="player",
                actor_ref_id="user-1",
                roll_result=roll_result,
                roll_type="skill",
            )
        self.assertEqual(roll_result.total, 19)

    async def test_ooc_multi_target_without_proximity_runtime_is_rejected(self) -> None:
        caster_state = self._caster_state()
        campaign_spell = self._campaign_spell()
        entry = MagicMock(party_id="party-1", campaign_id="camp-1")
        db = MagicMock()
        exec_results = [caster_state, campaign_spell]

        def exec_side_effect(*_args, **_kwargs):
            result = MagicMock()
            value = exec_results.pop(0) if exec_results else None
            result.first.return_value = value
            result.all.return_value = []
            return result

        db.exec.side_effect = exec_side_effect
        req = OutOfCombatCastRequest(
            spellId="spell-pwt-1",
            slotLevel=2,
            targetPlayerUserIds=["ally-a"],
        )
        actor_user = MagicMock(id="user-1")

        with patch("app.services.ooc_spell_cast_service._require_session_participant", return_value=None):
            with self.assertRaises(HTTPException) as ctx:
                await _cast_spell_out_of_combat_for_player(
                    entry=entry,
                    session_id="session-1",
                    req=req,
                    actor_user=actor_user,
                    caster_user_id="user-1",
                    session=db,
                    cast_by_gm=False,
                    ensure_session_state=MagicMock(return_value=caster_state),
                    finalize_session_state_data=lambda data, **_kwargs: data,
                    publish_state_update=AsyncMock(),
                    to_state_read=MagicMock(return_value=caster_state),
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("9m", ctx.exception.detail)
