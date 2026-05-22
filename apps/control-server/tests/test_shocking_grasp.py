from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from app.models.combat import CombatPhase, CombatState
from app.schemas.base_spell import BaseSpellCreate
from app.schemas.combat import CombatConsumeReactionRequest
from app.services.combat import CombatService, CombatServiceError


class ShockingGraspSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.spells = {s["canonicalKey"]: s for s in data.get("spells", [])}

    def test_seed_has_shocking_grasp_contract(self):
        s = self.spells["shocking_grasp"]
        self.assertEqual(s["level"], 0)
        self.assertEqual(s["school"], "evocation")
        self.assertEqual(s["rangeMeters"], 1.5)
        self.assertEqual(s["rangeKind"], "touch")
        self.assertEqual(s["attackType"], "melee_spell")
        self.assertEqual(s["damageDice"], "1d8")
        self.assertEqual(s["damageType"], "Lightning")
        self.assertFalse(s["concentration"])
        self.assertFalse(s["ritual"])
        self.assertEqual(
            s["attackAdvantageCondition"],
            {"type": "target_wearing_metal_armor"},
        )

    def test_seed_has_cantrip_scaling_and_reaction_rider(self):
        s = self.spells["shocking_grasp"]
        thresholds = s["cantripScaling"]["thresholds"]
        self.assertEqual(next(t for t in thresholds if t["characterLevel"] == 1)["damage"]["dice"], "1d8")
        self.assertEqual(next(t for t in thresholds if t["characterLevel"] == 5)["damage"]["dice"], "2d8")
        self.assertEqual(next(t for t in thresholds if t["characterLevel"] == 11)["damage"]["dice"], "3d8")
        self.assertEqual(next(t for t in thresholds if t["characterLevel"] == 17)["damage"]["dice"], "4d8")
        rider = s["effects"][0]
        self.assertEqual(rider["type"], "restrict_action")
        self.assertEqual(rider["params"]["action"], "reactions")
        self.assertEqual(rider["duration"]["type"], "until_turn_start")
        self.assertEqual(rider["duration"]["anchor"], "target")


class AttackAdvantageConditionSchemaTests(unittest.TestCase):
    def test_schema_accepts_canonical_attack_advantage_condition(self):
        payload = BaseSpellCreate.model_validate(
            {
                "system": "DND5E",
                "canonicalKey": "x",
                "nameEn": "X",
                "descriptionEn": "X",
                "level": 0,
                "school": "evocation",
                "attackAdvantageCondition": {"type": "target_wearing_metal_armor"},
            }
        )
        self.assertEqual(payload.attackAdvantageCondition.type, "target_wearing_metal_armor")

    def test_schema_rejects_unknown_attack_advantage_condition(self):
        with self.assertRaises(ValidationError):
            BaseSpellCreate.model_validate(
                {
                    "system": "DND5E",
                    "canonicalKey": "x",
                    "nameEn": "X",
                    "descriptionEn": "X",
                    "level": 0,
                    "school": "evocation",
                    "attackAdvantageCondition": {"type": "target_is_wet_and_sad"},
                }
            )


class ShockingGraspAdvantageRuntimeTests(unittest.TestCase):
    def test_spell_attack_uses_advantage_when_target_wears_metal_armor(self):
        attacker = {"id": "a1", "ref_id": "caster", "kind": "player", "display_name": "Caster", "active_effects": []}
        target = {
            "id": "t1",
            "ref_id": "target",
            "kind": "session_entity",
            "display_name": "Target",
            "active_effects": [],
            "equippedArmor": {"armorType": "heavy", "armorMaterial": "metal"},
            "wearingMetalArmor": False,
        }
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[attacker, target],
        )
        req = SimpleNamespace(
            has_advantage=False,
            has_disadvantage=False,
            roll_source="system",
            manual_roll=None,
            manual_rolls=None,
            concentration_roll_source="system",
            concentration_manual_roll=None,
        )
        targeting_result = SimpleNamespace(
            spatial_metadata=SimpleNamespace(cover="none", has_line_of_sight=True)
        )
        spell_context = {
            "attack_bonus": 0,
            "attack_advantage_condition": {"type": "target_wearing_metal_armor"},
            "damage_type": "Lightning",
        }

        fake_roll = SimpleNamespace(
            total=12,
            selected_roll=12,
            success=False,
            is_gm_roll=False,
            roll_source="system",
        )
        with patch(
            "app.services.combat_service.spells.spell_resolution_attack.resolve_attack_base",
            return_value=fake_roll,
        ) as resolve_roll, patch.object(
            CombatService,
            "_get_stats",
            return_value=(MagicMock(), 13, None, None, None, None),
        ):
            result = CombatService._resolve_spell_attack(
                db=MagicMock(),
                session_id="s1",
                state=state,
                attacker=attacker,
                target_p=target,
                spell_context=spell_context,
                req=req,
                is_gm=False,
                spell_mode="spell_attack",
                effect_kind="damage",
                effect_bonus=0,
                effect_roll_required=False,
                targeting_result=targeting_result,
            )

        self.assertIn("target_wearing_metal_armor", result.adv_ctx.advantage_sources)
        self.assertEqual(resolve_roll.call_args.kwargs["advantage_mode"], "advantage")


class ShockingGraspReactionBlockLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_restrict_reaction_expires_only_on_target_turn_start(self):
        caster = {"id": "p-caster", "display_name": "Caster", "active_effects": []}
        other = {"id": "p-other", "display_name": "Other", "active_effects": []}
        target = {
            "id": "p-target",
            "display_name": "Target",
            "active_effects": [
                {
                    "id": "e-reaction-block",
                    "kind": "spell_effect",
                    "duration_type": "until_turn_start",
                    "expires_on": "turn_start",
                    "expires_at_participant_id": "p-target",
                    "metadata": {
                        "declarative_effect": {
                            "type": "restrict_action",
                            "params": {"action": "reactions"},
                        },
                        "source_spell_key": "shocking_grasp",
                    },
                }
            ],
        }
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[caster, other, target],
        )

        expired_other = await CombatService._expire_effects_for_participant(
            "s1", state, "p-other", "turn_start"
        )
        self.assertEqual(expired_other, [])
        self.assertEqual(len(target["active_effects"]), 1)

        expired_target = await CombatService._expire_effects_for_participant(
            "s1", state, "p-target", "turn_start"
        )
        self.assertEqual(len(expired_target), 1)
        self.assertEqual(target["active_effects"], [])


class ReactionRestrictionEnforcementTests(unittest.IsolatedAsyncioTestCase):
    def _blocked_participant(self) -> dict:
        return {
            "id": "p1",
            "ref_id": "player-1",
            "kind": "player",
            "display_name": "Lia",
            "status": "active",
            "actor_user_id": "u1",
            "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
            "active_effects": [
                {
                    "id": "e1",
                    "kind": "spell_effect",
                    "duration_type": "until_turn_start",
                    "expires_on": "turn_start",
                    "expires_at_participant_id": "p1",
                    "metadata": {
                        "declarative_effect": {
                            "type": "restrict_action",
                            "params": {"action": "reactions"},
                        }
                    },
                }
            ],
        }

    def test_consume_turn_resource_blocks_reaction(self):
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._consume_turn_resource(self._blocked_participant(), "reaction")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Reaction is restricted by active effect", str(ctx.exception))

    async def test_consume_reaction_endpoint_blocks(self):
        blocked = self._blocked_participant()
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[blocked],
        )
        req = CombatConsumeReactionRequest(participant_id="p1")
        with patch("app.services.combat.CombatService.get_state", return_value=state):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService.consume_reaction(MagicMock(), "s1", req, "u1", False)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Reaction is restricted by active effect", str(ctx.exception))

    async def test_shield_reaction_cast_path_blocks(self):
        blocked = self._blocked_participant()
        state = CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                blocked,
                {
                    "id": "e1",
                    "ref_id": "enemy-1",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "team": "enemies",
                    "pending_attack": {
                        "id": "pa-1",
                        "type": "player_attack",
                        "target_ref_id": "player-1",
                        "roll": 17,
                        "target_ac": 12,
                    },
                },
            ],
        )
        req = SimpleNamespace(override_resource_limit=False)
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
        with patch.object(CombatService, "_emit_state", new_callable=AsyncMock), patch.object(
            CombatService, "_emit_log", new_callable=AsyncMock
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService._resolve_no_external_target_cast(
                    db=MagicMock(),
                    session_id="s1",
                    req=req,
                    state=state,
                    attacker=blocked,
                    attacker_model=MagicMock(),
                    spell_context=spell_context,
                    actor_user_id="u1",
                    is_gm=False,
                )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Reaction is restricted by active effect", str(ctx.exception))
