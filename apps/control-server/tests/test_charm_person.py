from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.base_spell import BaseSpellCreate
from app.schemas.combat import CombatCastSpellRequest
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService, CombatServiceError
from app.services.declarative_effect_lifecycle import remove_damage_terminated_effects_from_participant


def _make_player() -> dict:
    return {
        "id": "p1",
        "ref_id": "caster",
        "kind": "player",
        "display_name": "Lia",
        "initiative": 10,
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": "u1",
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_target(pid: str, ref_id: str, team: str = "enemies") -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": "session_entity",
        "display_name": f"Target {pid}",
        "initiative": 5,
        "status": "active",
        "team": team,
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_state(participants: list[dict]) -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
        use_map=False,
    )


def _make_charm_catalog_spell(max_targets: int = 1):
    return SimpleNamespace(
        canonical_key="charm_person",
        name_en="Charm Person",
        name_pt="Enfeitiçar Pessoa",
        level=1,
        resolution_type="control",
        damage_dice=None,
        heal_dice=None,
        damage_type=None,
        saving_throw="wisdom",
        save_success_outcome="none",
        upcast_json={"mode": "additional_targets", "perLevel": 1},
        cantrip_scaling_json=None,
        casting_time_type="action",
        target_type="ranged",
        selection_type="creature",
        origin_type="caster",
        target_anchor="selected_target",
        attack_type="none",
        range_kind="distance",
        effect_timing="immediate",
        area_shape=None,
        range_meters=9,
        duration="1 hour",
        concentration=False,
        cover_applies_to_save="none",
        max_targets=max_targets,
        requires_target_sight=True,
        requires_target_effect=True,
        requires_point_sight=False,
        requires_point_effect=False,
        effects_json=None,
    )


class CharmPersonSeedTests(unittest.TestCase):
    def test_charm_person_seed_contract(self):
        payload = json.loads(open(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"), encoding="utf-8").read())
        raw_spell = next(entry for entry in payload["spells"] if entry["canonicalKey"] == "charm_person")
        spell = BaseSpellCreate.model_validate(raw_spell)

        self.assertEqual(spell.level, 1)
        self.assertEqual(spell.school, "enchantment")
        self.assertEqual(spell.savingThrow, "WIS")
        self.assertEqual(raw_spell.get("saveSuccessOutcome"), "none")
        self.assertFalse(spell.concentration)
        self.assertEqual(spell.rangeMeters, 9)
        self.assertEqual(raw_spell.get("maxTargets"), 1)
        upcast = raw_spell.get("upcast") or {}
        self.assertEqual(upcast.get("mode"), "additional_targets")
        self.assertEqual(upcast.get("perLevel"), 1)


class CharmPersonUpcastContextTests(unittest.TestCase):
    def _resolve_context(self, slot_level: int) -> dict:
        state = _make_state([_make_player()])
        attacker_state = SessionState(
            id="ss-1",
            session_id="s1",
            player_user_id="u1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "charm_person", "level": 1, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=_make_charm_catalog_spell(1)),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            return CombatService.resolve_spell_context(
                MagicMock(),
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="charm_person",
                    spell_mode="saving_throw",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_upcast_max_targets_progression(self):
        self.assertEqual(self._resolve_context(1)["max_targets"], 1)
        self.assertEqual(self._resolve_context(2)["max_targets"], 2)
        self.assertEqual(self._resolve_context(3)["max_targets"], 3)
        self.assertEqual(self._resolve_context(4)["max_targets"], 4)


class CharmPersonCastFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_known_non_humanoid_is_rejected_without_slot_spend(self):
        state = _make_state([_make_player(), _make_target("e1", "enemy-a")])
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"1": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "charm_person", "name": "Charm Person", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="charm_person", target_ref_id="enemy-a")
        spell_context = {
            "spell_name": "Charm Person",
            "spell_canonical_key": "charm_person",
            "spell_mode": "saving_throw",
            "selection_type": "creature",
            "slot_level": 1,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "target_type": "ranged",
            "range_kind": "distance",
            "attack_type": "none",
            "requires_target_sight": True,
            "requires_target_effect": True,
            "concentration": False,
        }
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", return_value="undead"),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 0)
        self.assertEqual(state.participants[1].get("active_effects") or [], [])
        success_logs = [
            c for c in emit_log.await_args_list
            if "conjurou Charm Person" in ((c.args[4] or {}).get("message", "") if len(c.args) > 4 else "")
        ]
        self.assertEqual(success_logs, [])

    async def test_unknown_type_follows_hold_person_policy_and_allows_cast(self):
        state = _make_state([_make_player(), _make_target("e1", "enemy-a")])
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"1": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "charm_person", "name": "Charm Person", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="charm_person", target_ref_id="enemy-a")
        spell_context = {
            "spell_name": "Charm Person",
            "spell_canonical_key": "charm_person",
            "spell_mode": "saving_throw",
            "selection_type": "creature",
            "slot_level": 1,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "target_type": "ranged",
            "range_kind": "distance",
            "attack_type": "none",
            "requires_target_sight": True,
            "requires_target_effect": True,
            "concentration": False,
        }
        roll_fail = RollResult(
            event_id="r1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-a",
            actor_display_name="Target e1",
            rolls=[2],
            selected_roll=2,
            advantage_mode="normal",
            modifier_used=0,
            override_used=False,
            formula="1d20",
            total=2,
            ability="wisdom",
            dc=14,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", return_value=None),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch("app.services.combat_service.spells.automation._social_spells.resolve_saving_throw", return_value=roll_fail),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        self.assertFalse(result["is_saved"])
        self.assertEqual(len(state.participants[1].get("active_effects") or []), 1)

    async def test_hostile_teams_apply_initial_save_advantage(self):
        state = _make_state([_make_player(), _make_target("e1", "enemy-a", team="enemies")])
        roll_pass = RollResult(
            event_id="r1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-a",
            actor_display_name="Target e1",
            rolls=[7, 17],
            selected_roll=17,
            advantage_mode="advantage",
            modifier_used=0,
            override_used=False,
            formula="2d20kh1",
            total=17,
            ability="wisdom",
            dc=14,
            success=True,
            timestamp=datetime.now(timezone.utc),
        )

        with patch("app.services.combat_service.spells.automation._social_spells.resolve_saving_throw", return_value=roll_pass) as save_mock:
            await CombatService._cast_charm_person_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=MagicMock(),
                state=state,
                spell_context={"spell_name": "Charm Person", "spell_canonical_key": "charm_person", "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none"},
                target_participant=state.participants[1],
            )

        self.assertEqual(save_mock.call_args.kwargs.get("advantage_mode"), "advantage")

    async def test_non_hostile_teams_do_not_apply_initial_save_advantage(self):
        state = _make_state([_make_player(), _make_target("e1", "enemy-a", team="neutral")])
        roll_pass = RollResult(
            event_id="r1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-a",
            actor_display_name="Target e1",
            rolls=[12],
            selected_roll=12,
            advantage_mode="normal",
            modifier_used=0,
            override_used=False,
            formula="1d20",
            total=12,
            ability="wisdom",
            dc=14,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with patch("app.services.combat_service.spells.automation._social_spells.resolve_saving_throw", return_value=roll_pass) as save_mock:
            await CombatService._cast_charm_person_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=MagicMock(),
                state=state,
                spell_context={"spell_name": "Charm Person", "spell_canonical_key": "charm_person", "save_ability": "wisdom", "save_dc": 14, "save_success_outcome": "none"},
                target_participant=state.participants[1],
            )

        self.assertEqual(save_mock.call_args.kwargs.get("advantage_mode"), "normal")

    async def test_multi_target_atomic_failure_before_slot_consumption(self):
        state = _make_state([_make_player(), _make_target("e1", "enemy-a"), _make_target("e2", "enemy-b")])
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"3": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "charm_person", "name": "Charm Person", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="charm_person", target_ref_ids=["enemy-a", "enemy-b"], slot_level=3)
        spell_context = {
            "spell_name": "Charm Person",
            "spell_canonical_key": "charm_person",
            "spell_mode": "saving_throw",
            "selection_type": "creature",
            "slot_level": 3,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "target_type": "ranged",
            "range_kind": "distance",
            "attack_type": "none",
            "requires_target_sight": True,
            "requires_target_effect": True,
            "concentration": False,
            "max_targets": 3,
        }
        targeting_result = MagicMock(is_valid=True, validated_primary_target_ref_id="enemy-a", spatial_metadata=MagicMock(cover=None))

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", side_effect=["humanoid", "dragon"]),
            patch("app.services.combat_service.spells.cast_target.get_combat_targeting_service", return_value=MagicMock(validate=MagicMock(return_value=targeting_result))),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["3"]["used"], 0)
        self.assertEqual(state.participants[1].get("active_effects") or [], [])
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        success_logs = [
            c for c in emit_log.await_args_list
            if "conjurou Charm Person" in ((c.args[4] or {}).get("message", "") if len(c.args) > 4 else "")
        ]
        self.assertEqual(success_logs, [])

    async def test_break_on_damage_is_isolated_per_target(self):
        state = _make_state([
            _make_player(),
            _make_target("ally", "ally-1", team="players"),
            _make_target("a", "enemy-a"),
            _make_target("b", "enemy-b"),
            _make_target("c", "enemy-c", team="neutral"),
        ])

        for target in (state.participants[2], state.participants[3]):
            target["active_effects"] = [{
                "id": f"charm-{target['id']}",
                "kind": "condition",
                "condition_type": "charmed",
                "source_participant_id": "p1",
                "metadata": {
                    "source_spell_key": "charm_person",
                    "caster_participant_id": "p1",
                    "charmer_participant_id": "p1",
                    "target_knows_charmed_by_caster": True,
                    "termination_conditions": [{"type": "target_takes_damage_from_caster_or_allies"}],
                },
            }]

        removed_from_a = remove_damage_terminated_effects_from_participant(
            state,
            state.participants[2],
            attacker_participant_id="ally",
        )
        self.assertTrue(removed_from_a)
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        self.assertEqual(len(state.participants[3].get("active_effects") or []), 1)
        self.assertTrue((state.participants[3]["active_effects"][0].get("metadata") or {}).get("target_knows_charmed_by_caster"))

        removed_from_b_by_neutral = remove_damage_terminated_effects_from_participant(
            state,
            state.participants[3],
            attacker_participant_id="c",
        )
        self.assertFalse(removed_from_b_by_neutral)
        self.assertEqual(len(state.participants[3].get("active_effects") or []), 1)

    async def test_upcast_multi_target_then_damage_removes_only_damaged_target_effect(self):
        state = _make_state([
            _make_player(),
            _make_target("ally", "ally-1", team="players"),
            _make_target("a", "enemy-a"),
            _make_target("b", "enemy-b"),
        ])
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"2": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "charm_person", "name": "Charm Person", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="charm_person",
            target_ref_ids=["enemy-a", "enemy-b"],
            slot_level=2,
        )
        spell_context = {
            "spell_name": "Charm Person",
            "spell_canonical_key": "charm_person",
            "spell_mode": "saving_throw",
            "selection_type": "creature",
            "slot_level": 2,
            "action_cost": "action",
            "source_kind": "spell",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "target_type": "ranged",
            "range_kind": "distance",
            "attack_type": "none",
            "requires_target_sight": True,
            "requires_target_effect": True,
            "concentration": False,
            "max_targets": 2,
        }
        targeting_result = MagicMock(
            is_valid=True,
            validated_primary_target_ref_id="enemy-a",
            spatial_metadata=MagicMock(cover=None),
        )
        roll_fail_a = RollResult(
            event_id="r1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-a",
            actor_display_name="Target a",
            rolls=[5, 11],
            selected_roll=11,
            advantage_mode="advantage",
            modifier_used=0,
            override_used=False,
            formula="2d20kh1",
            total=11,
            ability="wisdom",
            dc=14,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )
        roll_fail_b = RollResult(
            event_id="r2",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-b",
            actor_display_name="Target b",
            rolls=[3, 7],
            selected_roll=7,
            advantage_mode="advantage",
            modifier_used=0,
            override_used=False,
            formula="2d20kh1",
            total=7,
            ability="wisdom",
            dc=14,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 10, 10, 10, 2, 3)),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService.resolve_effective_creature_type", side_effect=["humanoid", "humanoid"]),
            patch(
                "app.services.combat_service.spells.cast_target.get_combat_targeting_service",
                return_value=MagicMock(validate=MagicMock(return_value=targeting_result)),
            ),
            patch("app.services.combat_service.spells.automation._social_spells.resolve_saving_throw", side_effect=[roll_fail_a, roll_fail_b]),
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock),
        ):
            result = await CombatService.cast_spell(MagicMock(), "s1", req, "u1", False)

        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)
        self.assertEqual(len(state.participants[2].get("active_effects") or []), 1)
        self.assertEqual(len(state.participants[3].get("active_effects") or []), 1)
        self.assertEqual(result.get("target_count"), 2)

        removed_from_a = remove_damage_terminated_effects_from_participant(
            state,
            state.participants[2],
            attacker_participant_id="ally",
        )
        self.assertTrue(removed_from_a)
        self.assertEqual(state.participants[2].get("active_effects") or [], [])
        self.assertEqual(len(state.participants[3].get("active_effects") or []), 1)


if __name__ == "__main__":
    unittest.main()
