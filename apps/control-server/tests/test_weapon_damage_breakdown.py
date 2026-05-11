import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.schemas.combat import CombatResolveDamageRequest
from app.services.combat import CombatService


class TestWeaponDamageBreakdown(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = CombatState(
            id="combat-123",
            session_id="session-123",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-123",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": 15,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1",
                    "turn_resources": {"action_used": False},
                    "active_effects": [],
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-123",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "initiative": 10,
                    "status": "active",
                    "team": "enemies",
                    "visible": True,
                    "actor_user_id": None,
                    "active_effects": [],
                },
            ],
        )

    def _make_pending_attack(self, *, damage_dice="1d8", damage_bonus=3,
                              weapon_name="Longsword", is_critical=False,
                              damage_type="slashing"):
        return {
            "id": "attack-123",
            "type": "player_attack",
            "weapon_name": weapon_name,
            "weapon_item_id": "item-ls",
            "damage_dice": damage_dice,
            "damage_bonus": damage_bonus,
            "attack_bonus": 5,
            "damage_type": damage_type,
            "target_ref_id": "enemy-123",
            "target_kind": "session_entity",
            "target_display_name": "Goblin",
            "is_weapon_attack": True,
            "is_critical": is_critical,
            "roll": 18,
            "target_ac": 15,
        }

    def _make_req(self):
        return CombatResolveDamageRequest(pending_attack_id="attack-123")

    # ------------------------------------------------------------------
    # 1. base_weapon component
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_base_weapon(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(12, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", return_value=([5], 5)),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        breakdown = res["damage_breakdown"]
        base = next(c for c in breakdown["components"] if c["kind"] == "base_weapon")
        self.assertEqual(base["signed_total"], 5)
        self.assertEqual(base["dice"], "1d8")
        self.assertEqual(base["rolls"], [5])
        self.assertEqual(base["operation"], "add")
        self.assertEqual(base["damage_type"], "slashing")

    # ------------------------------------------------------------------
    # 2. ability_modifier component
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_ability_modifier(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack(damage_bonus=3)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(12, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", return_value=([6], 6)),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        breakdown = res["damage_breakdown"]
        ability = next(c for c in breakdown["components"] if c["kind"] == "ability_modifier")
        self.assertEqual(ability["signed_total"], 3)
        self.assertEqual(ability["operation"], "add")
        self.assertIsNone(ability["dice"])

    # ------------------------------------------------------------------
    # 3. ability_modifier omitted when zero
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_omits_ability_modifier_when_zero(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack(damage_bonus=0)

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(15, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", return_value=([5], 5)),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        kinds = [c["kind"] for c in res["damage_breakdown"]["components"]]
        self.assertNotIn("ability_modifier", kinds)

    # ------------------------------------------------------------------
    # 4. flat_modifier from damage_bonus effect
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_flat_modifier(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["active_effects"] = [
            {"id": "eff-df", "kind": "damage_bonus", "display_label": "Divine Favor", "numeric_value": 2},
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(10, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", return_value=([5], 5)),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        flat = next(c for c in res["damage_breakdown"]["components"] if c["kind"] == "flat_modifier")
        self.assertEqual(flat["signed_total"], 2)
        self.assertEqual(flat["source_label"], "Divine Favor")

    # ------------------------------------------------------------------
    # 5. modify_weapon_damage add
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_weapon_damage_modifier_add(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-enlarge",
                "kind": "modify_weapon_damage",
                "display_label": "Enlarge",
                "metadata": {"declarative_effect": {"params": {"dice": "1d4", "operation": "add"}}},
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(5, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([6], 6),   # base 1d8
                ([3], 3),   # enlarge 1d4
            ]),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        mod = next(c for c in res["damage_breakdown"]["components"] if c["kind"] == "weapon_damage_modifier")
        self.assertEqual(mod["signed_total"], 3)
        self.assertEqual(mod["operation"], "add")

    # ------------------------------------------------------------------
    # 6. modify_weapon_damage subtract
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_weapon_damage_modifier_subtract(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-reduce",
                "kind": "modify_weapon_damage",
                "display_label": "Reduce",
                "metadata": {"declarative_effect": {"params": {"dice": "1d4", "operation": "subtract"}}},
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(5, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([6], 6),   # base 1d8
                ([2], 2),   # reduce 1d4
            ]),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        mod = next(c for c in res["damage_breakdown"]["components"] if c["kind"] == "weapon_damage_modifier")
        self.assertEqual(mod["signed_total"], -2)
        self.assertEqual(mod["operation"], "subtract")

    # ------------------------------------------------------------------
    # 7. total, total_before_minimum, minimum_applied consistency
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_totals_match_applied_damage(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-reduce",
                "kind": "modify_weapon_damage",
                "display_label": "Reduce",
                "metadata": {"declarative_effect": {"params": {"dice": "1d4", "operation": "subtract"}}},
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(16, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([4], 4),   # base 1d8
                ([1], 1),   # reduce 1d4
            ]),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        bd = res["damage_breakdown"]
        # 4 (base) + 3 (ability) - 1 (reduce) = 6
        self.assertEqual(bd["total_before_minimum"], 6)
        self.assertIsNone(bd["minimum_applied"])
        self.assertEqual(bd["total"], 6)
        self.assertEqual(res["damage"], 6)

    # ------------------------------------------------------------------
    # 8. minimum_applied floor (dano minimo 1)
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_minimum_floor(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack(
            damage_dice="1d4", damage_bonus=-1, weapon_name="Dagger"
        )
        self.state.participants[0]["active_effects"] = [
            {
                "id": "eff-reduce",
                "kind": "modify_weapon_damage",
                "display_label": "Reduce",
                "metadata": {"declarative_effect": {"params": {
                    "dice": "1d4", "operation": "subtract", "minimum_total_damage": 1,
                }}},
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(19, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([1], 1),   # base 1d4 = 1
                ([4], 4),   # reduce 1d4 = 4
            ]),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        bd = res["damage_breakdown"]
        # 1 (base) - 1 (ability) - 4 (reduce) = -4
        self.assertEqual(bd["total_before_minimum"], -4)
        self.assertEqual(bd["minimum_applied"], 1)
        self.assertEqual(bd["total"], 1)
        self.assertEqual(res["damage"], 1)

    # ------------------------------------------------------------------
    # 9. extra_damage_rolls and extra_damage_label legacy fields
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_legacy_extra_damage_fields_populated(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["active_effects"] = [
            {"id": "eff-df", "kind": "damage_bonus", "display_label": "Divine Favor", "numeric_value": 2},
            {
                "id": "eff-reduce",
                "kind": "modify_weapon_damage",
                "display_label": "Reduce",
                "metadata": {"declarative_effect": {"params": {"dice": "1d4", "operation": "subtract"}}},
            },
        ]

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(10, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([5], 5),   # base
                ([3], 3),   # reduce
            ]),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        self.assertIn("extra_damage_rolls", res)
        self.assertIn("extra_damage_label", res)
        self.assertIn("Divine Favor", res["extra_damage_label"])
        self.assertIn("Reduce", res["extra_damage_label"])

    # ------------------------------------------------------------------
    # 10. Schema serialization round-trip
    # ------------------------------------------------------------------
    def test_combat_attack_result_serializes_breakdown(self):
        from app.schemas.combat import CombatAttackResult
        from app.schemas.roll import RollResult
        from datetime import datetime, timezone

        roll_result = RollResult(
            event_id="ev-1", roll_type="attack", actor_kind="player",
            actor_ref_id="p1", actor_display_name="Hero",
            rolls=[15, 8], selected_roll=15, advantage_mode="normal",
            modifier_used=5, override_used=False, formula="1d20+5",
            total=20, roll_source="system", timestamp=datetime.now(timezone.utc),
        )
        result = CombatAttackResult(
            roll=20, is_hit=True, damage=8, is_critical=False,
            roll_result=roll_result, target_ac=15,
            target_display_name="Goblin", target_kind="session_entity",
            weapon_name="Longsword", damage_dice="1d8", damage_bonus=3,
            attack_bonus=5, damage_rolls=[5],
            damage_breakdown={
                "total_before_minimum": 8,
                "minimum_applied": None,
                "total": 8,
                "components": [
                    {
                        "id": "c1", "kind": "base_weapon", "source_key": None,
                        "source_label": "Longsword", "dice": "1d8", "rolls": [5],
                        "operation": "add", "signed_total": 5,
                        "damage_type": "slashing", "doubled_on_critical": False,
                        "minimum_total_damage": None,
                    },
                    {
                        "id": "c2", "kind": "ability_modifier", "source_key": None,
                        "source_label": "Modificador", "dice": None, "rolls": [],
                        "operation": "add", "signed_total": 3,
                        "damage_type": "slashing", "doubled_on_critical": False,
                        "minimum_total_damage": None,
                    },
                ],
            },
            extra_damage_rolls=[],
            extra_damage_label=None,
        )

        data = result.model_dump()
        self.assertIn("damage_breakdown", data)
        self.assertEqual(data["damage_breakdown"]["total"], 8)
        self.assertEqual(len(data["damage_breakdown"]["components"]), 2)
        self.assertEqual(data["extra_damage_rolls"], [])
        self.assertIsNone(data["extra_damage_label"])

    # ------------------------------------------------------------------
    # 11. Hunter's Mark generates extra_damage component
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_hunters_mark(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(20, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(6, "", 20, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([5], 5),  # base
                ([4], 4),  # Hunter's Mark
            ]),
            patch("app.services.combat.CombatService._get_hunters_mark_effect_for_target", return_value={"id": "hm-1"}),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        hm = next(c for c in res["damage_breakdown"]["components"] if c["source_key"] == "hunters_mark")
        self.assertEqual(hm["kind"], "extra_damage")
        self.assertEqual(hm["signed_total"], 4)
        self.assertEqual(hm["dice"], "1d6")

    # ------------------------------------------------------------------
    # 12. Colossus Slayer generates extra_damage component
    # ------------------------------------------------------------------
    @patch("app.services.combat.CombatService._emit_and_persist_log")
    @patch("app.services.combat.CombatService._emit_state")
    @patch("app.services.combat.CombatService._emit_player_state_update")
    @patch("app.services.combat.CombatService._emit_entity_hp_update")
    async def test_breakdown_includes_colossus_slayer(self, *_mocks):
        self.state.participants[0]["pending_attack"] = self._make_pending_attack()
        self.state.participants[0]["turn_resources"] = {"action_used": False, "colossus_slayer_used": False}

        with (
            patch("app.services.combat.CombatService.get_state", return_value=self.state),
            patch("app.services.combat.CombatService._get_stats", side_effect=[
                (MagicMock(state_json={"class": "ranger", "features": ["colossus_slayer"]}), 10, 10, 10, 2, 0),
                (MagicMock(), 15, 10, 10, 2, 0),
            ]),
            patch("app.services.combat.CombatService._get_target_hp_snapshot", return_value=(18, 20)),
            patch("app.services.combat.CombatService._apply_damage_to_target", return_value=(2, "", 18, None)),
            patch("app.services.combat.CombatService._resolve_damage_roll", side_effect=[
                ([5], 5),  # base
                ([7], 7),  # Colossus Slayer
            ]),
            patch("app.services.combat.CombatService._get_hunters_mark_effect_for_target", return_value=None),
            patch("app.services.combat.CombatService._player_has_colossus_slayer", return_value=True),
        ):
            res = await CombatService.attack_damage(self.db, "session-123", self._make_req(), "user-1", True)

        cs = next(c for c in res["damage_breakdown"]["components"] if c["source_key"] == "colossus_slayer")
        self.assertEqual(cs["kind"], "extra_damage")
        self.assertEqual(cs["signed_total"], 7)
        self.assertEqual(cs["dice"], "1d8")
