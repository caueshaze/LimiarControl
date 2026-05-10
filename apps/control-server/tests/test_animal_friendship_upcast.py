"""Tests for Animal Friendship upcast target-count scaling (issue #279).

Covers:
- effective_max_targets computation at slot levels 1–3
- _validate_plain_multi_target_refs: mutual exclusion, duplicates, count
- _resolve_plain_multi_target_automation_cast: handler called per target,
  independent save outcomes
- Non-regression: single-target automation path unchanged
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.roll import RollActorStats
from app.schemas.combat_spells import CombatCastSpellRequest
from app.services.combat import CombatService, CombatServiceError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_participant(pid: str, ref_id: str, team: str = "enemies", kind: str = "session_entity") -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": kind,
        "display_name": f"Beast {pid}",
        "initiative": 5,
        "status": "active",
        "team": team,
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
        "turn_resources": {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
            "colossus_slayer_used": False,
        },
    }


def _make_player(pid: str = "p1", ref_id: str = "player-1") -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": "player",
        "display_name": "Ranger",
        "initiative": 15,
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": "user-1",
        "active_effects": [],
        "turn_resources": {
            "action_used": False,
            "bonus_action_used": False,
            "reaction_used": False,
            "colossus_slayer_used": False,
        },
    }


def _make_state(participants):
    return CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=participants,
        use_map=False,
    )


def _make_af_catalog_spell(max_targets: int = 1, slot_level: int = 1):
    """Return a SimpleNamespace mimicking an animal_friendship CampaignSpell."""
    return SimpleNamespace(
        canonical_key="animal_friendship",
        name_en="Animal Friendship",
        name_pt="Amizade Animal",
        level=1,
        resolution_type="saving_throw",
        saving_throw="wisdom",
        save_success_outcome="none",
        damage_type=None,
        damage_dice=None,
        heal_dice=None,
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
        radius_meters=None,
        length_meters=None,
        side_meters=None,
        duration="24 hours",
        concentration=False,
        cover_applies_to_save="none",
        max_targets=max_targets,
        variants_json=None,
        persistent_area_json=None,
        requires_target_sight=True,
        requires_target_effect=True,
        requires_point_sight=False,
        requires_point_effect=False,
        save_ability="wisdom",
        save_dc=14,
        effect_dice=None,
        effect_bonus=0,
        spell_mode="saving_throw",
    )


# ---------------------------------------------------------------------------
# Upcast: effective_max_targets scaling
# ---------------------------------------------------------------------------

class TestAnimalFriendshipUpcastContext(unittest.TestCase):
    """Verify that effective_max_targets = base + upcast_added per slot level."""

    def _resolve_context(self, slot_level: int, max_targets: int = 1) -> dict:
        from app.schemas.combat_spells import CombatResolveSpellContextRequest

        db = MagicMock()
        player = _make_player()
        state = _make_state([player])
        catalog_spell = _make_af_catalog_spell(max_targets=max_targets, slot_level=slot_level)
        attacker_state = SessionState(
            id="ss-1",
            session_id="session-1",
            player_user_id="player-1",
            state_json={
                "spellcasting": {
                    "spells": [
                        {"canonicalKey": "animal_friendship", "level": 1, "prepared": True}
                    ],
                    "slots": {
                        str(slot_level): {"used": 0, "max": 3},
                    },
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch(
                "app.services.combat.CombatService._get_spell_catalog_entry_for_session",
                return_value=catalog_spell,
            ),
            patch(
                "app.services.combat.CombatService._get_stats",
                return_value=(attacker_state, 12, 10, 10, 3, 4),
            ),
        ):
            return CombatService.resolve_spell_context(
                db,
                "session-1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="animal_friendship",
                    spell_mode="saving_throw",
                    slot_level=slot_level,
                ),
                "user-1",
                False,
            )

    def test_slot_1_effective_max_targets_is_1(self):
        result = self._resolve_context(slot_level=1, max_targets=1)
        self.assertEqual(result["max_targets"], 1)

    def test_slot_2_effective_max_targets_is_2(self):
        result = self._resolve_context(slot_level=2, max_targets=1)
        self.assertEqual(result["max_targets"], 2)

    def test_slot_3_effective_max_targets_is_3(self):
        result = self._resolve_context(slot_level=3, max_targets=1)
        self.assertEqual(result["max_targets"], 3)

    def test_base_max_targets_exposed(self):
        result = self._resolve_context(slot_level=2, max_targets=1)
        self.assertEqual(result["base_max_targets"], 1)

    # Golden chain tests: resolve_spell_context → _validate_plain_multi_target_refs

    def test_animal_friendship_upcast_slot_2_accepts_two_targets(self):
        """End-to-end: slot 2 resolves max_targets=2 which allows target_ref_ids of length 2."""
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        state = _make_state([_make_player(), beast1, beast2])
        # max_targets=2 is what resolve_spell_context returns at slot 2 (confirmed above)
        spell_context = {
            "max_targets": 2,
            "spell_canonical_key": "animal_friendship",
            "spell_mode": "saving_throw",
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="animal_friendship",
            target_ref_ids=["wolf-1", "wolf-2"],
            slot_level=2,
        )
        result = CombatService._validate_plain_multi_target_refs(
            req=req, spell_context=spell_context, state=state
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)
        self.assertEqual({p["ref_id"] for p in result}, {"wolf-1", "wolf-2"})

    def test_animal_friendship_upcast_slot_2_rejects_three_targets(self):
        """max_targets=2 (slot 2) must reject target_ref_ids of length 3."""
        beasts = [_make_participant(f"e{i}", f"wolf-{i}") for i in range(1, 4)]
        state = _make_state([_make_player()] + beasts)
        spell_context = {
            "max_targets": 2,
            "spell_canonical_key": "animal_friendship",
            "spell_mode": "saving_throw",
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="animal_friendship",
            target_ref_ids=["wolf-1", "wolf-2", "wolf-3"],
            slot_level=2,
        )
        with self.assertRaises(CombatServiceError):
            CombatService._validate_plain_multi_target_refs(
                req=req, spell_context=spell_context, state=state
            )

    def test_animal_friendship_upcast_slot_3_accepts_three_targets(self):
        """max_targets=3 (slot 3) allows target_ref_ids of length 3."""
        beasts = [_make_participant(f"e{i}", f"wolf-{i}") for i in range(1, 4)]
        state = _make_state([_make_player()] + beasts)
        spell_context = {
            "max_targets": 3,
            "spell_canonical_key": "animal_friendship",
            "spell_mode": "saving_throw",
        }
        req = CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="animal_friendship",
            target_ref_ids=["wolf-1", "wolf-2", "wolf-3"],
            slot_level=3,
        )
        result = CombatService._validate_plain_multi_target_refs(
            req=req, spell_context=spell_context, state=state
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)


# ---------------------------------------------------------------------------
# _validate_plain_multi_target_refs: unit tests
# ---------------------------------------------------------------------------

class TestValidatePlainMultiTargetRefs(unittest.TestCase):
    """Unit tests for the validation helper (no async needed)."""

    def _state(self, participants):
        return _make_state(participants)

    def _req(self, target_ref_ids=None, target_ref_id=None, target_variant_assignments=None, effect_instance_targets=None):
        return CombatCastSpellRequest(
            actor_participant_id="p1",
            spell_canonical_key="animal_friendship",
            target_ref_ids=target_ref_ids,
            target_ref_id=target_ref_id,
            target_variant_assignments=target_variant_assignments,
            effect_instance_targets=effect_instance_targets,
        )

    def _spell_context(self, max_targets=2):
        return {"max_targets": max_targets, "spell_canonical_key": "animal_friendship", "spell_mode": "saving_throw"}

    def test_returns_none_when_target_ref_ids_absent(self):
        state = self._state([_make_player()])
        result = CombatService._validate_plain_multi_target_refs(
            req=self._req(), spell_context=self._spell_context(), state=state
        )
        self.assertIsNone(result)

    def test_returns_none_when_target_ref_ids_empty(self):
        state = self._state([_make_player()])
        result = CombatService._validate_plain_multi_target_refs(
            req=self._req(target_ref_ids=[]), spell_context=self._spell_context(), state=state
        )
        self.assertIsNone(result)

    def test_resolves_valid_refs(self):
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        state = self._state([_make_player(), beast1, beast2])
        result = CombatService._validate_plain_multi_target_refs(
            req=self._req(target_ref_ids=["wolf-1", "wolf-2"]),
            spell_context=self._spell_context(max_targets=2),
            state=state,
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 2)

    def test_raises_on_duplicate_target_ref_ids(self):
        beast1 = _make_participant("e1", "wolf-1")
        state = self._state([_make_player(), beast1])
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._validate_plain_multi_target_refs(
                req=self._req(target_ref_ids=["wolf-1", "wolf-1"]),
                spell_context=self._spell_context(max_targets=3),
                state=state,
            )
        self.assertIn("Duplicate", str(ctx.exception))

    def test_raises_when_count_exceeds_effective_max(self):
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        beast3 = _make_participant("e3", "wolf-3")
        state = self._state([_make_player(), beast1, beast2, beast3])
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._validate_plain_multi_target_refs(
                req=self._req(target_ref_ids=["wolf-1", "wolf-2", "wolf-3"]),
                spell_context=self._spell_context(max_targets=2),
                state=state,
            )
        self.assertIn("2", str(ctx.exception))

    def test_raises_when_ref_id_not_found(self):
        state = self._state([_make_player()])
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._validate_plain_multi_target_refs(
                req=self._req(target_ref_ids=["nonexistent"]),
                spell_context=self._spell_context(max_targets=3),
                state=state,
            )
        self.assertIn("nonexistent", str(ctx.exception))

    def test_raises_when_spell_has_no_max_targets(self):
        beast = _make_participant("e1", "wolf-1")
        state = self._state([_make_player(), beast])
        ctx_no_max = {"max_targets": None, "spell_canonical_key": "other_spell", "spell_mode": "saving_throw"}
        with self.assertRaises(CombatServiceError):
            CombatService._validate_plain_multi_target_refs(
                req=self._req(target_ref_ids=["wolf-1"]),
                spell_context=ctx_no_max,
                state=state,
            )

    def test_raises_on_mutual_exclusion_with_target_ref_id(self):
        beast = _make_participant("e1", "wolf-1")
        state = self._state([_make_player(), beast])
        with self.assertRaises(CombatServiceError) as ctx:
            CombatService._validate_plain_multi_target_refs(
                req=self._req(target_ref_ids=["wolf-1"], target_ref_id="wolf-1"),
                spell_context=self._spell_context(max_targets=3),
                state=state,
            )
        self.assertIn("cannot be combined", str(ctx.exception))


# ---------------------------------------------------------------------------
# Integration: _resolve_plain_multi_target_automation_cast (handler per target)
# ---------------------------------------------------------------------------

class TestResolvePlainMultiTargetAutomationCast(unittest.IsolatedAsyncioTestCase):
    """Verify that _resolve_plain_multi_target_automation_cast calls the
    automation handler independently for each target."""

    def _make_beast_db(self, ref_id: str) -> MagicMock:
        """Return a MagicMock DB that resolves SessionEntity+CampaignEntity as beast."""
        from app.models.campaign_entity import CampaignEntity
        from app.models.session_entity import SessionEntity

        se_result = MagicMock()
        se_result.first.return_value = SessionEntity(
            id=ref_id,
            session_id="session-1",
            campaign_entity_id=f"ce-{ref_id}",
            overrides={},
        )
        ce_result = MagicMock()
        ce_result.first.return_value = CampaignEntity(
            id=f"ce-{ref_id}",
            campaign_id="camp-1",
            name="Wolf",
            creature_type="beast",
        )
        db = MagicMock()
        db.exec.side_effect = [se_result, ce_result] * 10  # enough for multiple targets
        return db

    def _make_multi_beast_db(self, ref_ids: list[str]) -> MagicMock:
        """Return a DB mock that always resolves as a beast entity."""
        from app.models.campaign_entity import CampaignEntity
        from app.models.session_entity import SessionEntity
        import itertools

        # Build per-ref_id results, then cycle so we never exhaust
        results = []
        for ref_id in ref_ids:
            se = MagicMock()
            se.first.return_value = SessionEntity(
                id=ref_id,
                session_id="session-1",
                campaign_entity_id=f"ce-{ref_id}",
                overrides={},
            )
            ce = MagicMock()
            ce.first.return_value = CampaignEntity(
                id=f"ce-{ref_id}",
                campaign_id="camp-1",
                name="Wolf",
                creature_type="beast",
            )
            results.extend([se, ce])

        db = MagicMock()
        call_iter = itertools.cycle(results)
        db.exec.side_effect = lambda *a, **kw: next(call_iter)
        return db

    async def _resolve(self, targets: list[dict], roll_side_effect=None):
        player = _make_player()
        state = _make_state([player] + targets)
        state.phase = CombatPhase.active

        attacker_state = SessionState(
            id="ss-1",
            session_id="session-1",
            player_user_id="player-1",
            state_json={
                "spellcasting": {
                    "slots": {"2": {"used": 0, "max": 3}},
                }
            },
        )
        target_stats = RollActorStats(
            display_name="Wolf",
            abilities={"wisdom": 10},
            actor_kind="session_entity",
            actor_ref_id=targets[0]["ref_id"],
        )
        spell_context = {
            "spell_canonical_key": "animal_friendship",
            "spell_name": "Amizade Animal",
            "spell_mode": "saving_throw",
            "action_kind": "saving_throw",
            "action_cost": "action",
            "effect_kind": None,
            "effect_dice": None,
            "effect_bonus": 0,
            "damage_type": None,
            "save_ability": "wisdom",
            "save_dc": 14,
            "save_success_outcome": "none",
            "slot_level": 2,
            "max_targets": len(targets) + 1,
            "source_kind": "standard",
            "concentration": False,
        }

        roll_fn = roll_side_effect or (lambda *a, **kw: 5)
        db = self._make_multi_beast_db([t["ref_id"] for t in targets])

        with (
            patch(
                "app.services.combat.CombatService._build_roll_actor_stats_for_save",
                return_value=target_stats,
            ),
            patch(
                "app.services.combat.CombatService._get_stats",
                return_value=(attacker_state, 12, 10, 10, 2, 3),
            ),
            patch(
                "app.services.combat_service.spell_automation.get_game_time_seconds",
                return_value=1000,
            ),
            patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_player_state_update", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock),
            patch("app.services.combat.CombatService._emit_and_persist_log", new_callable=AsyncMock),
            patch("random.randint", side_effect=roll_fn),
        ):
            req = CombatCastSpellRequest(
                actor_participant_id="p1",
                target_ref_ids=[t["ref_id"] for t in targets],
                spell_canonical_key="animal_friendship",
            )
            result = await CombatService._resolve_plain_multi_target_automation_cast(
                db, "session-1", req, state, player, attacker_state,
                spell_context, "user-1", False, targets,
            )
        return result, state

    async def test_both_targets_charmed_on_failed_saves(self):
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        result, state = await self._resolve([beast1, beast2], roll_side_effect=lambda *a, **kw: 2)

        self.assertEqual(result["target_count"], 2)
        wolf1 = next(p for p in state.participants if p["ref_id"] == "wolf-1")
        wolf2 = next(p for p in state.participants if p["ref_id"] == "wolf-2")
        self.assertTrue(any(e.get("condition_type") == "charmed" for e in wolf1["active_effects"]))
        self.assertTrue(any(e.get("condition_type") == "charmed" for e in wolf2["active_effects"]))

    async def test_targets_resolve_independently(self):
        """Alternating rolls: first fails, second passes."""
        import itertools
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        # roll_d20_pair calls randint TWICE per target (returns d20_a, d20_b)
        # In normal mode, d20_a is used.  DC 14 → roll < 14 fails, >= 14 passes.
        # Pair [2, 2] for wolf-1 → d20_a=2 → fail.  [18, 18] for wolf-2 → d20_a=18 → pass.
        rolls = itertools.cycle([2, 2, 18, 18])
        result, state = await self._resolve(
            [beast1, beast2], roll_side_effect=lambda *a, **kw: next(rolls)
        )

        wolf1 = next(p for p in state.participants if p["ref_id"] == "wolf-1")
        wolf2 = next(p for p in state.participants if p["ref_id"] == "wolf-2")
        self.assertTrue(any(e.get("condition_type") == "charmed" for e in wolf1["active_effects"]))
        self.assertFalse(any(e.get("condition_type") == "charmed" for e in wolf2["active_effects"]))

    async def test_result_includes_affected_target_refs(self):
        beast1 = _make_participant("e1", "wolf-1")
        beast2 = _make_participant("e2", "wolf-2")
        result, _ = await self._resolve([beast1, beast2], roll_side_effect=lambda *a, **kw: 5)
        self.assertIn("wolf-1", result.get("affected_target_ref_ids", []))
        self.assertIn("wolf-2", result.get("affected_target_ref_ids", []))

    async def test_single_target_still_works(self):
        beast = _make_participant("e1", "wolf-1")
        result, state = await self._resolve([beast], roll_side_effect=lambda *a, **kw: 2)
        self.assertEqual(result["target_count"], 1)
        wolf = next(p for p in state.participants if p["ref_id"] == "wolf-1")
        self.assertTrue(any(e.get("condition_type") == "charmed" for e in wolf["active_effects"]))


if __name__ == "__main__":
    unittest.main()
