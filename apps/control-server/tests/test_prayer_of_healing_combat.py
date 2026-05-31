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
