from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService, CombatServiceError
from app.schemas.combat import CombatCastSpellRequest


class ShieldHelpersTests(unittest.TestCase):
    def test_upsert_shield_effect_replaces_existing(self):
        participant = {
            "id": "p1",
            "active_effects": [
                {"id": "a", "kind": "temp_ac_bonus", "numeric_value": 5, "metadata": {"source_spell_key": "shield"}},
                {"id": "b", "kind": "temp_ac_bonus", "numeric_value": 2, "metadata": {"source_spell_key": "other"}},
            ],
        }
        CombatService._upsert_shield_temp_ac_effect(participant, source_participant_id="p1")
        effects = participant["active_effects"]
        shield = [e for e in effects if e.get("kind") == "temp_ac_bonus" and (e.get("metadata") or {}).get("source_spell_key") == "shield"]
        self.assertEqual(len(shield), 1)
        self.assertEqual(shield[0]["numeric_value"], 5)
        self.assertEqual(shield[0]["expires_on"], "turn_start")

    def test_is_shielded_for_magic_missile(self):
        participant = {
            "active_effects": [
                {"kind": "temp_ac_bonus", "numeric_value": 5, "metadata": {"source_spell_key": "shield"}}
            ]
        }
        self.assertTrue(CombatService._is_shielded_for_magic_missile(participant))


class ShieldTriggerTests(unittest.IsolatedAsyncioTestCase):
    async def test_shield_requires_incoming_hit_trigger(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "player-1", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "turn_resources": {"reaction_used": False}},
                {"id": "e1", "ref_id": "enemy-1", "kind": "session_entity", "display_name": "Goblin", "status": "active", "team": "enemies"},
            ],
        )
        req = MagicMock(override_resource_limit=False)
        spell_context = {"spell_canonical_key": "shield", "source_kind": "spell", "slot_level": 1}
        with self.assertRaises(CombatServiceError):
            await CombatService._resolve_no_external_target_cast(
                db=MagicMock(),
                session_id="s1",
                req=req,
                state=state,
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                spell_context=spell_context,
                actor_user_id="u1",
                is_gm=False,
            )


class ShieldCastE2ETests(unittest.IsolatedAsyncioTestCase):
    async def test_cast_spell_consumes_reaction_and_slot_and_clears_pending_when_shield_turns_hit_into_miss(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "lia",
                    "kind": "player",
                    "display_name": "Lia",
                    "status": "active",
                    "team": "players",
                    "actor_user_id": "u1",
                    "turn_resources": {"reaction_used": False},
                },
                {
                    "id": "e1",
                    "ref_id": "goblin",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "team": "enemies",
                    "pending_attack": {
                        "id": "pa-1",
                        "type": "player_attack",
                        "target_ref_id": "lia",
                        "roll": 17,
                        "target_ac": 15,
                    },
                },
            ],
        )
        attacker_state = MagicMock()
        attacker_state.state_json = {
            "spellcasting": {
                "slots": {"1": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "shield", "name": "Shield", "prepared": True, "level": 1}],
            }
        }
        req = CombatCastSpellRequest(actor_participant_id="p1", spell_canonical_key="shield")
        spell_context = {
            "spell_name": "Shield",
            "spell_canonical_key": "shield",
            "spell_mode": "utility",
            "selection_type": "none",
            "slot_level": 1,
            "action_cost": "reaction",
            "source_kind": "spell",
            "effect_kind": None,
        }

        def _mock_get_stats(*args, **kwargs):
            if kwargs.get("combat_state") is not None:
                return (attacker_state, 20, None, None, 2, 3)
            return (attacker_state, 15, None, None, 2, 3)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._resolve_player_spell_context", return_value=spell_context),
            patch("app.services.combat.CombatService._get_stats", side_effect=_mock_get_stats),
            patch.object(CombatService, "_emit_and_persist_log", new_callable=AsyncMock) as emit_log,
            patch.object(CombatService, "_emit_state", new_callable=AsyncMock),
        ):
            db = MagicMock()
            result = await CombatService.cast_spell(db, "s1", req, "u1", False)

        self.assertEqual(result["spell_canonical_key"], "shield")
        self.assertNotIn("pending_attack", state.participants[1])
        self.assertEqual(attacker_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        self.assertTrue(state.participants[0]["turn_resources"]["reaction_used"])
        shield_effects = [
            e for e in state.participants[0].get("active_effects", [])
            if e.get("kind") == "temp_ac_bonus" and (e.get("metadata") or {}).get("source_spell_key") == "shield"
        ]
        self.assertEqual(len(shield_effects), 1)
        emit_log.assert_awaited()


class MagicMissileInterceptTests(unittest.IsolatedAsyncioTestCase):
    async def test_shielded_target_instances_are_zeroed(self):
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {"id": "p1", "ref_id": "caster", "kind": "player", "display_name": "Mage", "status": "active", "team": "players", "turn_resources": {}},
                {"id": "p2", "ref_id": "lia", "kind": "player", "display_name": "Lia", "status": "active", "team": "players", "turn_resources": {}, "active_effects": [{"kind": "temp_ac_bonus", "numeric_value": 5, "metadata": {"source_spell_key": "shield"}}]},
                {"id": "p3", "ref_id": "theo", "kind": "player", "display_name": "Theo", "status": "active", "team": "players", "turn_resources": {}},
            ],
        )
        validated_targets = [
            {"instance_index": 1, "target_ref_id": "lia", "participant": state.participants[1]},
            {"instance_index": 2, "target_ref_id": "lia", "participant": state.participants[1]},
            {"instance_index": 3, "target_ref_id": "theo", "participant": state.participants[2]},
        ]
        spell_context = {"spell_canonical_key": "magic_missile", "spell_mode": "direct_damage", "action_cost": "action", "effect_kind": "damage", "source_kind": "spell", "slot_level": 1, "spell_name": "Magic Missile"}
        req = MagicMock(override_resource_limit=False)

        with patch.object(CombatService, "_consume_turn_resource", return_value=False), \
             patch.object(CombatService, "_consume_player_spell_slot"), \
             patch.object(CombatService, "_resolve_instance_direct", side_effect=[
                 {"target_ref_id": "lia", "target_display_name": "Lia", "target_kind": "player", "damage": 4, "healing": 0, "new_hp": 10, "previous_hp": 14},
                 {"target_ref_id": "lia", "target_display_name": "Lia", "target_kind": "player", "damage": 3, "healing": 0, "new_hp": 7, "previous_hp": 10},
                 {"target_ref_id": "theo", "target_display_name": "Theo", "target_kind": "player", "damage": 5, "healing": 0, "new_hp": 8, "previous_hp": 13},
             ]), \
             patch.object(CombatService, "_emit_player_state_update"), \
             patch.object(CombatService, "_emit_state"), \
             patch.object(CombatService, "_emit_and_persist_log"), \
             patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 10, None, None, None, None)):
            db = MagicMock()
            result = await CombatService._resolve_multi_instance_cast(
                db=db,
                session_id="s1",
                req=req,
                state=state,
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                spell_context=spell_context,
                actor_user_id="u1",
                is_gm=False,
                validated_targets=validated_targets,
            )

        outcomes = result["effect_instance_outcomes"]
        self.assertEqual(outcomes[0]["damage"], 0)
        self.assertEqual(outcomes[1]["damage"], 0)
        self.assertEqual(outcomes[2]["damage"], 5)


if __name__ == "__main__":
    unittest.main()
