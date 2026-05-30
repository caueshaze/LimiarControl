"""Tests for Chill Touch / Toque Necrótico.

Covers:
- Seed contract: level=0, necromancy, ranged_spell, 1d8 Necrotic, cantrip scaling
- Targeting semantics: selection_type=creature, ranged_spell, distance, immediate
- Automation: hit/miss flow, prevent_healing rider, undead attack-disadvantage rider
- prevent_healing enforcement in _apply_healing_to_target
- resolve_attack_advantage with applies_when_attacking_participant_id filter
- Effect expiration at caster's turn start (not target's, not others')
"""

from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService
from app.services.combat_service.condition_effects_attacks import resolve_attack_advantage
from app.services.combat_service.damage_core import CombatDamageCoreMixin
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state() -> CombatState:
    return CombatState(
        id="c1",
        session_id="s1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        use_map=False,
        participants=[
            {
                "id": "caster-p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Feiticeiro",
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "u1",
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
            {
                "id": "target-p2",
                "ref_id": "npc-1",
                "kind": "session_entity",
                "display_name": "Goblin",
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": [],
                "turn_resources": {
                    "action_used": False,
                    "bonus_action_used": False,
                    "reaction_used": False,
                },
            },
        ],
    )


def _ctx(effect_dice: str = "1d8") -> dict:
    return {
        "spell_canonical_key": "chill_touch",
        "spell_name": "Toque Necrótico",
        "slot_level": 0,
        "spell_level": 0,
        "spell_mode": "spell_attack",
        "effect_dice": effect_dice,
        "attack_bonus": 5,
    }


def _mock_hit_roll(nat: int = 15) -> MagicMock:
    r = MagicMock()
    r.success = True
    r.total = nat
    r.selected_roll = nat
    r.is_gm_roll = False
    return r


def _mock_miss_roll() -> MagicMock:
    r = MagicMock()
    r.success = False
    r.total = 3
    r.selected_roll = 3
    r.is_gm_roll = False
    return r


# ---------------------------------------------------------------------------
# Seed contract
# ---------------------------------------------------------------------------

class ChillTouchSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        spells = {s["canonicalKey"]: s for s in data.get("spells", [])}
        cls.entry = spells.get("chill_touch")

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "chill_touch not found in seed")

    def test_canonical_key(self):
        self.assertEqual(self.entry["canonicalKey"], "chill_touch")

    def test_level_zero(self):
        self.assertEqual(self.entry["level"], 0)

    def test_school_necromancy(self):
        self.assertEqual(self.entry["school"], "necromancy")

    def test_no_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_no_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_classes(self):
        for cls_name in ["Sorcerer", "Warlock", "Wizard"]:
            self.assertIn(cls_name, self.entry.get("classesJson", []))

    def test_range_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 36)

    def test_attack_type_ranged_spell(self):
        self.assertEqual(self.entry["attackType"], "ranged_spell")

    def test_range_kind_distance(self):
        self.assertEqual(self.entry["rangeKind"], "distance")

    def test_damage_dice_1d8(self):
        self.assertEqual(self.entry["damageDice"], "1d8")

    def test_damage_type_necrotic(self):
        self.assertEqual(self.entry["damageType"], "Necrotic")

    def test_no_saving_throw(self):
        self.assertNotIn("savingThrow", self.entry)

    def test_no_upcast(self):
        self.assertIsNone(self.entry.get("upcast"))

    def test_cantrip_scaling_has_four_thresholds(self):
        cs = self.entry.get("cantripScaling", {})
        self.assertEqual(cs.get("scalingMode"), "character_level")
        self.assertEqual(cs.get("scalingEffectType"), "damage_dice")
        thresholds = cs.get("thresholds", [])
        self.assertEqual(len(thresholds), 4)
        by_level = {t["characterLevel"]: t["damage"]["dice"] for t in thresholds}
        self.assertEqual(by_level[1], "1d8")
        self.assertEqual(by_level[5], "2d8")
        self.assertEqual(by_level[11], "3d8")
        self.assertEqual(by_level[17], "4d8")


# ---------------------------------------------------------------------------
# Targeting semantics
# ---------------------------------------------------------------------------

class ChillTouchTargetingSemanticsTests(unittest.TestCase):
    def test_semantics_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "chill_touch"})
        self.assertEqual(sem.selection_type, "creature")
        self.assertEqual(sem.target_anchor, "selected_target")
        self.assertEqual(sem.attack_type, "ranged_spell")
        self.assertEqual(sem.range_kind, "distance")
        self.assertEqual(sem.effect_timing, "immediate")


# ---------------------------------------------------------------------------
# Automation
# ---------------------------------------------------------------------------

class ChillTouchAutomationTests(unittest.IsolatedAsyncioTestCase):
    """Tests for _cast_chill_touch_automation handler."""

    def _attacker(self, state: CombatState) -> dict:
        return state.participants[0]

    def _target(self, state: CombatState) -> dict:
        return state.participants[1]

    def _attacker_model(self) -> SessionState:
        return SessionState(
            id="st1",
            session_id="s1",
            player_user_id="player-1",
            state_json={"spellcasting": {"slots": {"1": {"used": 0, "max": 2}}}},
        )

    async def _cast(
        self,
        *,
        hit: bool = True,
        nat: int = 15,
        creature_type: str = "humanoid",
        damage: int = 5,
        effect_dice: str = "1d8",
        req=None,
        state: CombatState | None = None,
    ) -> tuple[dict, CombatState]:
        if req is None:
            req = SimpleNamespace()
        if state is None:
            state = _state()
        attacker = self._attacker(state)
        target = self._target(state)
        attacker_model = self._attacker_model()

        roll = _mock_hit_roll(nat) if hit else _mock_miss_roll()
        adv_ctx_mock = MagicMock()
        adv_ctx_mock.advantage_sources = []
        adv_ctx_mock.disadvantage_sources = []
        adv_ctx_mock.consumed_effect_ids_on_roll = []

        with (
            patch("app.services.combat_service.spells.automation._chill_touch.resolve_attack_base", return_value=roll),
            patch("app.services.combat_service.spells.automation._chill_touch.resolve_attack_advantage", return_value=adv_ctx_mock),
            patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, 30, 30, 3, 3)),
            patch.object(CombatService, "_apply_spell_effect", return_value=(25, "", 30, None)),
            patch.object(CombatService, "_resolve_damage_roll", return_value=([damage], damage)),
            patch.object(CombatService, "resolve_effective_creature_type", return_value=creature_type),
        ):
            result = await CombatService._cast_chill_touch_automation(
                MagicMock(), "s1",
                attacker=attacker,
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_ctx(effect_dice),
                target_participant=target,
            )
        return result, state

    async def test_action_kind_is_spell_attack(self):
        result, _ = await self._cast()
        self.assertEqual(result["action_kind"], "spell_attack")

    async def test_hit_is_hit_true(self):
        result, _ = await self._cast(hit=True)
        self.assertTrue(result["is_hit"])

    async def test_miss_is_hit_false(self):
        result, _ = await self._cast(hit=False)
        self.assertFalse(result["is_hit"])

    async def test_hit_causes_nonzero_damage(self):
        result, _ = await self._cast(hit=True, damage=5)
        self.assertGreater(result["damage"], 0)

    async def test_miss_causes_zero_damage(self):
        result, _ = await self._cast(hit=False)
        self.assertEqual(result["damage"], 0)

    async def test_hit_creates_prevent_healing_effect_on_target(self):
        result, state = await self._cast(hit=True)
        target = state.participants[1]
        effects = target.get("active_effects") or []
        prevent_effects = [
            e for e in effects
            if (e.get("metadata") or {}).get("prevent_healing") is True
        ]
        self.assertEqual(len(prevent_effects), 1)

    async def test_miss_does_not_create_prevent_healing_effect(self):
        result, state = await self._cast(hit=False)
        target = state.participants[1]
        effects = target.get("active_effects") or []
        prevent_effects = [
            e for e in effects
            if (e.get("metadata") or {}).get("prevent_healing") is True
        ]
        self.assertEqual(len(prevent_effects), 0)

    async def test_hit_non_undead_no_undead_rider(self):
        result, state = await self._cast(hit=True, creature_type="humanoid")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        undead_riders = [
            e for e in effects
            if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"
        ]
        self.assertEqual(len(undead_riders), 0)

    async def test_hit_undead_creates_disadvantage_rider(self):
        result, state = await self._cast(hit=True, creature_type="undead")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        undead_riders = [
            e for e in effects
            if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"
        ]
        self.assertEqual(len(undead_riders), 1)

    async def test_undead_rider_has_caster_participant_filter(self):
        state = _state()
        result, state = await self._cast(hit=True, creature_type="undead", state=state)
        target = state.participants[1]
        effects = target.get("active_effects") or []
        rider = next(
            (e for e in effects
             if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"),
            None,
        )
        self.assertIsNotNone(rider)
        params = (rider["metadata"]["declarative_effect"]["params"])
        self.assertEqual(params["applies_when_attacking_participant_id"], "caster-p1")

    async def test_undead_rider_consume_on_apply_false(self):
        result, state = await self._cast(hit=True, creature_type="undead")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        rider = next(
            (e for e in effects
             if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"),
            None,
        )
        self.assertIsNotNone(rider)
        params = rider["metadata"]["declarative_effect"]["params"]
        self.assertFalse(params["consume_on_apply"])

    async def test_undead_rider_source_label_is_chill_touch(self):
        result, state = await self._cast(hit=True, creature_type="undead")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        rider = next(
            (e for e in effects
             if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"),
            None,
        )
        self.assertIsNotNone(rider)
        params = rider["metadata"]["declarative_effect"]["params"]
        self.assertEqual(params["source"], "chill_touch")

    async def test_miss_no_undead_rider(self):
        result, state = await self._cast(hit=False, creature_type="undead")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        undead_riders = [
            e for e in effects
            if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"
        ]
        self.assertEqual(len(undead_riders), 0)

    async def test_hit_no_concentration_group(self):
        result, _ = await self._cast(hit=True)
        self.assertIsNone(result.get("concentration_group"))

    async def test_hit_no_slot_consumption(self):
        attacker_model = self._attacker_model()
        state = _state()
        roll = _mock_hit_roll()
        adv_ctx_mock = MagicMock()
        adv_ctx_mock.advantage_sources = []
        adv_ctx_mock.disadvantage_sources = []
        adv_ctx_mock.consumed_effect_ids_on_roll = []

        with (
            patch("app.services.combat_service.spells.automation._chill_touch.resolve_attack_base", return_value=roll),
            patch("app.services.combat_service.spells.automation._chill_touch.resolve_attack_advantage", return_value=adv_ctx_mock),
            patch.object(CombatService, "_get_stats", return_value=(MagicMock(), 12, 30, 30, 3, 3)),
            patch.object(CombatService, "_apply_spell_effect", return_value=(25, "", 30, None)),
            patch.object(CombatService, "_resolve_damage_roll", return_value=([5], 5)),
            patch.object(CombatService, "resolve_effective_creature_type", return_value="humanoid"),
        ):
            await CombatService._cast_chill_touch_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=attacker_model,
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=state,
                spell_context=_ctx(),
                target_participant=state.participants[1],
            )
        slots = (attacker_model.state_json.get("spellcasting") or {}).get("slots") or {}
        self.assertEqual(slots.get("1", {}).get("used"), 0)

    async def test_requires_target_raises_400(self):
        from app.services.combat_service.exceptions import CombatServiceError
        state = _state()
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_chill_touch_automation(
                MagicMock(), "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=SimpleNamespace(),
                state=state,
                spell_context=_ctx(),
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_nat_20_is_critical(self):
        result, _ = await self._cast(hit=True, nat=20)
        self.assertTrue(result.get("is_critical"))

    async def test_non_nat_20_is_not_critical(self):
        result, _ = await self._cast(hit=True, nat=15)
        self.assertFalse(result.get("is_critical"))

    async def test_prevent_healing_effect_expires_at_caster(self):
        result, state = await self._cast(hit=True)
        target = state.participants[1]
        effects = target.get("active_effects") or []
        prevent = next(
            (e for e in effects if (e.get("metadata") or {}).get("prevent_healing") is True),
            None,
        )
        self.assertIsNotNone(prevent)
        self.assertEqual(prevent["expires_at_participant_id"], "caster-p1")
        self.assertEqual(prevent["expires_on"], "turn_start")

    async def test_undead_rider_expires_at_caster(self):
        result, state = await self._cast(hit=True, creature_type="undead")
        target = state.participants[1]
        effects = target.get("active_effects") or []
        rider = next(
            (e for e in effects
             if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"),
            None,
        )
        self.assertIsNotNone(rider)
        self.assertEqual(rider["expires_at_participant_id"], "caster-p1")
        self.assertEqual(rider["expires_on"], "turn_start")


# ---------------------------------------------------------------------------
# Prevent healing enforcement
# ---------------------------------------------------------------------------

class ChillTouchPreventHealingEnforcementTests(unittest.TestCase):
    """Tests for _participant_has_prevent_healing and _apply_healing_to_target."""

    def _participant_with_prevent_healing(self, ref_id: str = "ref-1") -> dict:
        return {
            "id": "p1",
            "ref_id": ref_id,
            "kind": "player",
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_key": "chill_touch",
                        "prevent_healing": True,
                    },
                }
            ],
        }

    def _participant_without_effect(self, ref_id: str = "ref-1") -> dict:
        return {
            "id": "p1",
            "ref_id": ref_id,
            "kind": "player",
            "active_effects": [],
        }

    def _participant_with_false_flag(self, ref_id: str = "ref-1") -> dict:
        return {
            "id": "p1",
            "ref_id": ref_id,
            "kind": "player",
            "active_effects": [
                {
                    "id": "eff-1",
                    "kind": "spell_effect",
                    "metadata": {"prevent_healing": False},
                }
            ],
        }

    def test_has_prevent_healing_with_effect(self):
        p = self._participant_with_prevent_healing()
        self.assertTrue(CombatService._participant_has_prevent_healing(p))

    def test_has_prevent_healing_without_effect(self):
        p = self._participant_without_effect()
        self.assertFalse(CombatService._participant_has_prevent_healing(p))

    def test_has_prevent_healing_with_false_flag(self):
        p = self._participant_with_false_flag()
        self.assertFalse(CombatService._participant_has_prevent_healing(p))

    def test_apply_healing_blocked_when_effect_present(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0, use_map=False,
            participants=[self._participant_with_prevent_healing("ref-blocked")],
        )
        mock_model = MagicMock()
        mock_model.state_json = {"currentHP": 20, "maxHP": 30}

        with patch.object(CombatService, "_get_stats", return_value=(mock_model, 15, 20, 30, 2, 2)):
            new_hp, msg, prev_hp = CombatService._apply_healing_to_target(
                MagicMock(), "ref-blocked", "player", 10, state
            )

        self.assertEqual(new_hp, 20)
        self.assertEqual(prev_hp, 20)
        self.assertIn("impedida", msg.lower())

    def test_apply_healing_normal_without_effect(self):
        state = CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0, use_map=False,
            participants=[self._participant_without_effect("ref-normal")],
        )
        mock_model = MagicMock()
        mock_model.state_json = {"currentHP": 20, "maxHP": 30, "deathSaves": None}
        mock_model.current_hp = 20

        with (
            patch.object(CombatService, "_get_stats", return_value=(mock_model, 15, 20, 30, 2, 2)),
            patch("app.services.combat_service.damage_core.finalize_session_state_data", side_effect=lambda x: x),
            patch.object(CombatService, "_sync_participant_status", return_value="active"),
            patch.object(CombatService, "_is_player_dead_state", return_value=False),
        ):
            new_hp, msg, prev_hp = CombatService._apply_healing_to_target(
                MagicMock(), "ref-normal", "player", 10, state
            )

        self.assertNotIn("impedida", msg.lower())

    def test_apply_healing_without_state_not_blocked(self):
        mock_model = MagicMock()
        mock_model.state_json = {"currentHP": 20, "maxHP": 30, "deathSaves": None}
        mock_model.current_hp = 20

        with (
            patch.object(CombatService, "_get_stats", return_value=(mock_model, 15, 20, 30, 2, 2)),
            patch("app.services.combat_service.damage_core.finalize_session_state_data", side_effect=lambda x: x),
            patch.object(CombatService, "_sync_participant_status", return_value="active"),
            patch.object(CombatService, "_is_player_dead_state", return_value=False),
        ):
            new_hp, msg, prev_hp = CombatService._apply_healing_to_target(
                MagicMock(), "ref-no-state", "player", 10, state=None
            )

        self.assertNotIn("impedida", msg.lower())


# ---------------------------------------------------------------------------
# Undead rider — resolve_attack_advantage filter
# ---------------------------------------------------------------------------

class ChillTouchUndeadRiderAdvantageTests(unittest.TestCase):
    """Tests for applies_when_attacking_participant_id in resolve_attack_advantage."""

    def _undead_with_rider(self, caster_id: str) -> dict:
        return {
            "id": "undead-1",
            "active_effects": [
                {
                    "id": "rider-1",
                    "kind": "spell_effect",
                    "metadata": {
                        "source_spell_key": "chill_touch",
                        "declarative_effect": {
                            "type": "roll_disadvantage_modifier",
                            "params": {
                                "mode": "disadvantage",
                                "roll_types": ["attack"],
                                "applies_when_attacking_participant_id": caster_id,
                                "consume_on_apply": False,
                                "source": "chill_touch",
                            },
                        },
                    },
                }
            ],
        }

    def _participant(self, pid: str) -> dict:
        return {"id": pid, "active_effects": []}

    def test_undead_with_rider_attacking_caster_has_disadvantage(self):
        undead = self._undead_with_rider("caster-1")
        caster = self._participant("caster-1")
        ctx = resolve_attack_advantage(undead, caster, "ranged")
        self.assertEqual(ctx.result, "disadvantage")
        self.assertIn("chill_touch", ctx.disadvantage_sources)

    def test_undead_with_rider_attacking_other_is_normal(self):
        undead = self._undead_with_rider("caster-1")
        other = self._participant("other-1")
        ctx = resolve_attack_advantage(undead, other, "ranged")
        self.assertEqual(ctx.result, "normal")
        self.assertNotIn("chill_touch", ctx.disadvantage_sources)

    def test_no_rider_attacking_caster_is_normal(self):
        humanoid = self._participant("humanoid-1")
        caster = self._participant("caster-1")
        ctx = resolve_attack_advantage(humanoid, caster, "ranged")
        self.assertEqual(ctx.result, "normal")

    def test_rider_without_applies_when_is_backward_compatible(self):
        attacker = {
            "id": "attacker-1",
            "active_effects": [
                {
                    "id": "old-eff",
                    "kind": "spell_effect",
                    "metadata": {
                        "declarative_effect": {
                            "type": "roll_disadvantage_modifier",
                            "params": {
                                "mode": "disadvantage",
                                "roll_types": ["attack"],
                                "consume_on_apply": True,
                                "source": "vicious_mockery",
                            },
                        }
                    },
                }
            ],
        }
        any_target = self._participant("any-1")
        ctx = resolve_attack_advantage(attacker, any_target, "melee")
        self.assertEqual(ctx.result, "disadvantage")

    def test_rider_consume_on_apply_false_not_consumed_on_attack(self):
        undead = self._undead_with_rider("caster-1")
        caster = self._participant("caster-1")
        ctx = resolve_attack_advantage(undead, caster, "ranged")
        self.assertEqual(ctx.result, "disadvantage")
        self.assertEqual(ctx.consumed_effect_ids_on_roll, [])


# ---------------------------------------------------------------------------
# Expiration
# ---------------------------------------------------------------------------

class ChillTouchExpirationTests(unittest.IsolatedAsyncioTestCase):
    """Riders expire at caster's turn_start, not target's or others'."""

    def _state_with_target_effects(self, caster_id: str) -> CombatState:
        return CombatState(
            id="c1", session_id="s1", phase=CombatPhase.active,
            round=1, current_turn_index=0, use_map=False,
            participants=[
                {
                    "id": caster_id,
                    "ref_id": "player-caster",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "team": "players",
                    "active_effects": [],
                },
                {
                    "id": "target-1",
                    "ref_id": "npc-target",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "status": "active",
                    "team": "enemies",
                    "active_effects": [
                        {
                            "id": "ph-eff",
                            "kind": "spell_effect",
                            "duration_type": "until_turn_start",
                            "expires_on": "turn_start",
                            "expires_at_participant_id": caster_id,
                            "metadata": {
                                "source_spell_key": "chill_touch",
                                "prevent_healing": True,
                            },
                        },
                        {
                            "id": "rider-eff",
                            "kind": "spell_effect",
                            "duration_type": "until_turn_start",
                            "expires_on": "turn_start",
                            "expires_at_participant_id": caster_id,
                            "metadata": {
                                "source_spell_key": "chill_touch",
                                "declarative_effect": {
                                    "type": "roll_disadvantage_modifier",
                                    "params": {
                                        "mode": "disadvantage",
                                        "roll_types": ["attack"],
                                        "applies_when_attacking_participant_id": caster_id,
                                        "consume_on_apply": False,
                                        "source": "chill_touch",
                                    },
                                },
                            },
                        },
                    ],
                },
                {
                    "id": "other-1",
                    "ref_id": "npc-other",
                    "kind": "session_entity",
                    "display_name": "Orc",
                    "status": "active",
                    "team": "enemies",
                    "active_effects": [],
                },
            ],
        )

    async def test_prevent_healing_survives_target_turn_start(self):
        state = self._state_with_target_effects("caster-p")
        await CombatService._expire_effects_for_participant("s1", state, "target-1", "turn_start")
        effects = state.participants[1].get("active_effects") or []
        self.assertTrue(any((e.get("metadata") or {}).get("prevent_healing") is True for e in effects))

    async def test_prevent_healing_survives_other_turn_start(self):
        state = self._state_with_target_effects("caster-p")
        await CombatService._expire_effects_for_participant("s1", state, "other-1", "turn_start")
        effects = state.participants[1].get("active_effects") or []
        self.assertTrue(any((e.get("metadata") or {}).get("prevent_healing") is True for e in effects))

    async def test_prevent_healing_expires_at_caster_turn_start(self):
        state = self._state_with_target_effects("caster-p")
        await CombatService._expire_effects_for_participant("s1", state, "caster-p", "turn_start")
        effects = state.participants[1].get("active_effects") or []
        self.assertFalse(any((e.get("metadata") or {}).get("prevent_healing") is True for e in effects))

    async def test_undead_rider_expires_at_caster_turn_start(self):
        state = self._state_with_target_effects("caster-p")
        await CombatService._expire_effects_for_participant("s1", state, "caster-p", "turn_start")
        effects = state.participants[1].get("active_effects") or []
        riders = [
            e for e in effects
            if (e.get("metadata") or {}).get("declarative_effect", {}).get("type") == "roll_disadvantage_modifier"
        ]
        self.assertEqual(len(riders), 0)

    async def test_both_effects_gone_after_caster_turn(self):
        state = self._state_with_target_effects("caster-p")
        await CombatService._expire_effects_for_participant("s1", state, "caster-p", "turn_start")
        effects = state.participants[1].get("active_effects") or []
        self.assertEqual(len(effects), 0)
