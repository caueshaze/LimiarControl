from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService


class TestPrayerOfHealingCombatStart(unittest.IsolatedAsyncioTestCase):
    async def test_start_prayer_of_healing_long_cast_consumes_resources_and_creates_pending_cast(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=4,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "team": "players",
                    "turn_resources": {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": False,
                        "colossus_slayer_used": False,
                        "compelled_duel_movement_free": False,
                        "crown_of_madness_forced_attack_pending": False,
                        "crown_of_madness_forced_attack_resolved": False,
                        "crown_of_madness_forced_attack_skipped": False,
                    },
                },
                {
                    "id": "p2",
                    "ref_id": "player-2",
                    "kind": "player",
                    "display_name": "Ally",
                    "status": "active",
                    "team": "players",
                },
            ],
        )
        attacker = state.participants[0]
        attacker_model = MagicMock()
        attacker_model.state_json = {
            "spellcasting": {
                "slots": {"2": {"used": 0, "max": 3}},
            }
        }
        req = SimpleNamespace(override_resource_limit=False)
        spell_context = {
            "spell_canonical_key": "prayer_of_healing",
            "spell_name": "Oração de Cura",
            "slot_level": 2,
            "action_cost": "action",
        }
        db = MagicMock()

        with patch.object(CombatService, "_get_stats", return_value=(MagicMock(), None, None, None, None, None)), patch.object(
            CombatService, "_emit_player_state_update", new=AsyncMock()
        ), patch.object(CombatService, "_emit_state", new=AsyncMock()), patch.object(
            CombatService, "_emit_and_persist_log", new=AsyncMock()
        ):
            result = await CombatService._start_prayer_of_healing_long_cast(
                db,
                "session-1",
                req=req,
                state=state,
                attacker=attacker,
                attacker_model=attacker_model,
                spell_context=spell_context,
                actor_user_id="user-1",
                is_gm=False,
                targets=[state.participants[0], state.participants[1]],
            )

        self.assertEqual(attacker_model.state_json["spellcasting"]["slots"]["2"]["used"], 1)
        self.assertEqual(len(state.pending_spell_casts), 1)
        pending = state.pending_spell_casts[0]
        self.assertEqual(pending["spell_key"], "prayer_of_healing")
        self.assertEqual(pending["required_rounds"], 100)
        self.assertEqual(pending["completed_rounds"], 1)
        self.assertEqual(pending["remaining_rounds"], 99)
        self.assertTrue(pending["maintained_this_turn"])
        self.assertEqual(result["pending_cast"]["remaining_rounds"], 99)
        self.assertEqual(result["healing"], 0)

    async def test_maintain_pending_cast_increments_progress(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=4,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "user-1",
                    "turn_resources": {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": False,
                        "colossus_slayer_used": False,
                        "compelled_duel_movement_free": False,
                        "crown_of_madness_forced_attack_pending": False,
                        "crown_of_madness_forced_attack_resolved": False,
                        "crown_of_madness_forced_attack_skipped": False,
                    },
                }
            ],
            pending_spell_casts=[
                {
                    "id": "pc-1",
                    "spell_key": "prayer_of_healing",
                    "spell_name": "Oração de Cura",
                    "caster_participant_id": "p1",
                    "status": "casting",
                    "required_rounds": 100,
                    "completed_rounds": 1,
                    "remaining_rounds": 99,
                    "requires_action_each_turn": True,
                    "maintained_this_turn": False,
                }
            ],
        )
        db = MagicMock()
        with patch.object(CombatService, "get_state", return_value=state), patch.object(
            CombatService, "_emit_state", new=AsyncMock()
        ), patch.object(CombatService, "_emit_log", new=AsyncMock()):
            result = await CombatService.resolve_pending_spell_cast_maintain(
                db,
                "session-1",
                actor_user_id="user-1",
                is_gm=False,
                actor_participant_id="p1",
                pending_cast_id="pc-1",
                override_resource_limit=False,
            )
        self.assertTrue(result["maintained"])
        self.assertEqual(result["completedRounds"], 2)
        self.assertEqual(result["remainingRounds"], 98)
        self.assertTrue(state.pending_spell_casts[0]["maintained_this_turn"])

    async def test_turn_end_cancels_pending_cast_when_not_maintained(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=4,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "player-1", "kind": "player", "display_name": "Caster", "status": "active"}
            ],
            pending_spell_casts=[
                {
                    "id": "pc-1",
                    "spell_key": "prayer_of_healing",
                    "spell_name": "Oração de Cura",
                    "caster_participant_id": "p1",
                    "status": "casting",
                    "required_rounds": 100,
                    "completed_rounds": 5,
                    "remaining_rounds": 95,
                    "requires_action_each_turn": True,
                    "maintained_this_turn": False,
                }
            ],
        )
        with patch.object(CombatService, "_emit_log", new=AsyncMock()):
            await CombatService._resolve_pending_spell_cast_maintenance_on_turn_end(
                "session-1",
                state,
                state.participants[0],
            )
        self.assertEqual(state.pending_spell_casts, [])

    async def test_maintain_completes_prayer_of_healing_and_applies_healing(self):
        target_model = MagicMock()
        target_model.state_json = {"currentHP": 5, "maxHP": 20}
        caster_model = MagicMock()
        caster_model.state_json = {"spellcasting": {"slots": {"2": {"used": 1, "max": 3}}}}
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=4,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-1",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "user-1",
                    "turn_resources": {
                        "action_used": False,
                        "bonus_action_used": False,
                        "reaction_used": False,
                        "colossus_slayer_used": False,
                        "compelled_duel_movement_free": False,
                        "crown_of_madness_forced_attack_pending": False,
                        "crown_of_madness_forced_attack_resolved": False,
                        "crown_of_madness_forced_attack_skipped": False,
                    },
                },
                {
                    "id": "p2",
                    "ref_id": "player-2",
                    "kind": "player",
                    "display_name": "Ally",
                    "status": "active",
                    "team": "players",
                },
            ],
            local_distances={"player-1": {"player-2": 6}},
            pending_spell_casts=[
                {
                    "id": "pc-1",
                    "spell_key": "prayer_of_healing",
                    "spell_name": "Oração de Cura",
                    "caster_participant_id": "p1",
                    "caster_ref_id": "player-1",
                    "target_ref_ids": ["player-2"],
                    "slot_level": 2,
                    "status": "casting",
                    "required_rounds": 100,
                    "completed_rounds": 99,
                    "remaining_rounds": 1,
                    "requires_action_each_turn": True,
                    "requires_concentration_during_casting": True,
                    "maintained_this_turn": False,
                }
            ],
        )
        db = MagicMock()

        def _stats_side_effect(_db, ref_id, kind, _session_id, *args, **kwargs):
            if ref_id == "player-1":
                return (caster_model, 10, 10, 10, 3, 3)
            if ref_id == "player-2":
                return (target_model, 10, 10, 10, 1, 2)
            raise AssertionError(ref_id)

        with patch.object(CombatService, "get_state", return_value=state), patch.object(
            CombatService, "_get_stats", side_effect=_stats_side_effect
        ), patch.object(CombatService, "_emit_state", new=AsyncMock()), patch.object(
            CombatService, "_emit_log", new=AsyncMock()
        ), patch(
            "app.services.combat_service.spell_automation._roll_dice_expression",
            return_value=([4, 4], 8),
        ):
            result = await CombatService.resolve_pending_spell_cast_maintain(
                db,
                "session-1",
                actor_user_id="user-1",
                is_gm=False,
                actor_participant_id="p1",
                pending_cast_id="pc-1",
                override_resource_limit=False,
            )

        self.assertEqual(state.pending_spell_casts, [])
        self.assertEqual(target_model.state_json["currentHP"], 16)
        self.assertIn("completion", result)
        self.assertEqual(result["completion"]["healing_total"], 11)
        self.assertEqual(result["completion"]["range_validation"], "best_effort")

    def test_interrupt_pending_cast_after_damage_cancels_cast(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[],
            pending_spell_casts=[
                {
                    "id": "pc-1",
                    "spell_key": "prayer_of_healing",
                    "caster_participant_id": "p1",
                    "status": "casting",
                    "requires_concentration_during_casting": True,
                }
            ],
        )
        changed = CombatService._interrupt_pending_spell_cast_after_damage(
            state,
            participant_id="p1",
            concentration_check={"success": False},
            new_hp=5,
        )
        self.assertTrue(changed)
        self.assertEqual(state.pending_spell_casts, [])
