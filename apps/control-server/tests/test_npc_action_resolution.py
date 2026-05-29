from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import app.services.combat_service.npc_actions as _npc_mod
from app.services.combat_service.condition_effects_saves import modify_saving_throw
from app.services.combat_service import CombatService


def _attacker(creature_type="fiend"):
    return {
        "id": "npc-1",
        "ref_id": "npc-ref",
        "kind": "session_entity",
        "display_name": "NPC",
        "creature_type": creature_type,
        "active_effects": [],
    }


def _target_with_protection():
    protected = ["aberration", "celestial", "elemental", "fey", "fiend", "undead"]
    return {
        "id": "tgt-1",
        "ref_id": "tgt-ref",
        "kind": "player",
        "display_name": "Hero",
        "active_effects": [
            {
                "id": "eff-1",
                "kind": "spell_effect",
                "metadata": {
                    "source_spell_key": "protection_from_evil_and_good",
                    "declarative_save_effect": {
                        "type": "saving_throw_advantage_against_creature_types",
                        "params": {
                            "mode": "advantage",
                            "source": "protection_from_evil_and_good",
                            "source_creature_types": protected,
                            "roll_types": ["saving_throw"],
                            "consume_on_apply": False,
                        },
                    },
                },
            }
        ],
    }


class NpcSaveActionSourceParticipantTests(unittest.TestCase):
    """NPC save actions must pass source_participant=attacker for source-aware effects."""

    def _call(self, attacker, target):
        """Execute _resolve_npc_action_result with saving_throw action_kind."""
        tr = MagicMock()
        tr.is_valid = True
        tr.spatial_metadata.cover = None
        tr.validated_primary_target_ref_id = target["ref_id"]

        state = MagicMock()
        state.use_map = False
        state.participants = [attacker, target]

        req = MagicMock()
        req.roll_source = "system"
        req.manual_roll = None
        req.manual_rolls = []

        with (
            patch.object(_npc_mod, "get_combat_targeting_service") as mock_gcts,
            patch.object(CombatService, "_build_npc_targeting_intent", return_value=MagicMock()),
            patch(
                "app.services.combat_service.npc_action_resolution.resolve_cover_save_dc",
                return_value=(14, None),
            ),
            patch(
                "app.services.combat_service.npc_action_resolution.modify_saving_throw",
                wraps=modify_saving_throw,
            ) as spy_modify,
            patch(
                "app.services.combat_service.npc_action_resolution.resolve_saving_throw",
                return_value=MagicMock(success=True, total=20, check_modifier_sources=[]),
            ),
            patch.object(
                CombatService,
                "_build_roll_actor_stats_for_save",
                return_value=MagicMock(),
            ),
            patch.object(CombatService, "_apply_roll_bonus_dice_to_roll_result"),
        ):
            mock_gcts.return_value.validate.return_value = tr
            result = CombatService._resolve_npc_action_result(
                MagicMock(),
                "session-1",
                req,
                True,
                state=state,
                attacker=attacker,
                resolved_action={"saveAbility": "wisdom", "saveDc": 14},
                action_name="test",
                action_kind="saving_throw",
                damage_type=None,
                target_p=target,
            )
            return result, spy_modify.call_args

    def test_fiend_attacker_grants_advantage_via_protection(self):
        attacker = _attacker("fiend")
        target = _target_with_protection()
        result, call_args = self._call(attacker, target)
        _, kwargs = call_args
        self.assertIs(kwargs.get("source_participant"), attacker)
        self.assertEqual(result["save_mod"].result, "advantage")

    def test_humanoid_attacker_no_advantage(self):
        attacker = _attacker("humanoid")
        target = _target_with_protection()
        result, call_args = self._call(attacker, target)
        _, kwargs = call_args
        self.assertIs(kwargs.get("source_participant"), attacker)
        self.assertEqual(result["save_mod"].result, "normal")


if __name__ == "__main__":
    unittest.main()
