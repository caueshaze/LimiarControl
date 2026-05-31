from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import unittest

from app.models.combat import CombatPhase, CombatState
from app.services.combat import CombatService
from app.services.combat_service.spells.spell_context_resolve import SpellContextResolveMixin
from app.services.out_of_combat_cast import check_out_of_combat_cast_eligibility
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


def _seed_entry() -> dict:
    seed_path = Path(__file__).resolve().parents[3] / "Base" / "base_spells.seed.json"
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    spells = payload.get("spells") or []
    for spell in spells:
        if spell.get("canonicalKey") == "hellish_rebuke":
            return spell
    raise AssertionError("hellish_rebuke not found in seed")


def test_hellish_rebuke_seed_contract():
    entry = _seed_entry()
    assert entry["level"] == 1
    assert entry["school"] == "evocation"
    assert "Warlock" in entry["classesJson"]
    assert entry["castingTimeType"] == "reaction"
    assert entry["castingTime"] == "1 reaction"
    assert entry["rangeMeters"] == 18
    assert entry["durationSeconds"] == 0
    assert entry["concentration"] is False
    assert entry["ritual"] is False
    assert entry["resolutionType"] == "damage"
    assert entry["attackType"] == "save"
    assert entry["savingThrowAbility"] == "DEX"
    assert entry["saveSuccessOutcome"] == "half_damage"
    assert entry["damageDice"] == "2d10"
    assert entry["damageType"] == "fire"
    assert entry["outOfCombatCastable"] is False



def test_hellish_rebuke_targeting_semantics_override():
    semantics = resolve_spell_targeting_semantics({"canonicalKey": "hellish_rebuke"}).to_dict()
    assert semantics == {
        "selection_type": "reaction_source",
        "origin_type": "damaged_caster",
        "target_anchor": "damage_source",
        "attack_type": "save",
        "range_kind": "distance",
        "effect_timing": "reaction",
    }



def test_hellish_rebuke_context_metadata():
    utility = SpellContextResolveMixin.UTILITY_SPELL_CONTEXT_META["hellish_rebuke"]
    reaction = utility["reaction"]
    assert reaction["trigger"] == "damaged_by_visible_creature_within_range"
    assert reaction["consumesReaction"] is True
    assert reaction["requiresVisibleSource"] is True
    assert reaction["rangeMeters"] == 18
    save = utility["save"]
    assert save["ability"] == "dexterity"
    assert save["effect"] == "half_damage"
    damage = utility["damage"]
    assert damage["dice"] == "2d10"
    assert damage["type"] == "fire"
    assert damage["upcastDicePerSlotAboveBase"] == "1d10"


def test_hellish_rebuke_reaction_opportunity_creation_from_damage_event():
    state = CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=2,
        current_turn_index=1,
        participants=[
            {
                "id": "caster",
                "ref_id": "caster-ref",
                "status": "active",
                "turn_resources": {"reaction_used": False},
                "active_effects": [],
            },
            {"id": "attacker", "ref_id": "attacker-ref", "status": "active"},
        ],
    )
    created = CombatService._maybe_create_hellish_rebuke_reaction_opportunity(
        state,
        target_participant=state.participants[0],
        source_participant_id="attacker",
        damage_taken=8,
        damage_event_id="damage-1",
    )
    assert created is True
    assert len(state.reaction_opportunities) == 1
    opportunity = state.reaction_opportunities[0]
    assert opportunity["kind"] == "damage_taken"
    assert opportunity["spell_key"] == "hellish_rebuke"
    assert opportunity["actor_participant_id"] == "caster"
    assert opportunity["source_participant_id"] == "attacker"
    assert opportunity["damage_event_id"] == "damage-1"
    assert opportunity["status"] == "available"


def test_reaction_opportunity_expires_on_turn_boundary():
    state = CombatState(
        id="combat-1",
        session_id="session-1",
        phase=CombatPhase.active,
        round=2,
        current_turn_index=1,
        participants=[],
        reaction_opportunities=[
            {"id": "op-1", "status": "available", "kind": "damage_taken"},
            {"id": "op-2", "status": "used", "kind": "damage_taken"},
        ],
    )
    changed = CombatService._expire_reaction_opportunities_turn_boundary(state)
    assert changed is True
    assert state.reaction_opportunities == [{"id": "op-2", "status": "used", "kind": "damage_taken"}]


def test_hellish_rebuke_not_ooc_castable():
    spell = SimpleNamespace(
        canonical_key="hellish_rebuke",
        out_of_combat_castable=False,
        level=1,
        effects_json=[],
        variants_json=[],
    )
    ok, reason = check_out_of_combat_cast_eligibility(
        spell=spell,
        state_json={},
        slot_level=1,
        variant_key=None,
    )
    assert ok is False
    assert isinstance(reason, str)


class TestHellishRebukeResolver(unittest.IsolatedAsyncioTestCase):
    async def test_hellish_rebuke_resolve_success_consumes_reaction_slot_and_deals_damage(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=2,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster",
                    "ref_id": "caster-ref",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "actor_user_id": "user-1",
                    "turn_resources": {"reaction_used": False},
                    "active_effects": [],
                },
                {
                    "id": "attacker",
                    "ref_id": "attacker-ref",
                    "kind": "session_entity",
                    "display_name": "Attacker",
                    "status": "active",
                    "active_effects": [],
                },
            ],
            local_distances={"caster-ref": {"attacker-ref": 6}},
            reaction_opportunities=[
                {
                    "id": "op-1",
                    "kind": "damage_taken",
                    "spell_key": "hellish_rebuke",
                    "actor_participant_id": "caster",
                    "source_participant_id": "attacker",
                    "status": "available",
                }
            ],
        )
        actor_model = MagicMock()
        actor_model.state_json = {
            "spellcasting": {
                "slots": {"1": {"used": 0, "max": 2}},
                "spells": [{"canonicalKey": "hellish_rebuke", "level": 1, "prepared": True}],
            }
        }
        db = MagicMock()
        roll_result = SimpleNamespace(success=False, total=7, check_modifier_sources=[])

        with patch.object(CombatService, "get_state", return_value=state), patch.object(
            CombatService, "_get_stats", return_value=(actor_model, 10, 2, 3, 2, 13)
        ), patch.object(
            CombatService, "_build_roll_actor_stats_for_save", return_value=MagicMock()
        ), patch(
            "app.services.combat_service.spell_automation.resolve_saving_throw",
            return_value=roll_result,
        ), patch(
            "app.services.combat_service.spell_automation._roll_dice_expression",
            return_value=([8, 5], 13),
        ), patch.object(
            CombatService, "_apply_damage_to_target", return_value=(4, "", 17, None)
        ), patch.object(
            CombatService, "_emit_state", new=AsyncMock()
        ), patch.object(
            CombatService, "_emit_and_persist_log", new=AsyncMock()
        ):
            result = await CombatService.resolve_hellish_rebuke_reaction(
                db,
                "session-1",
                actor_user_id="user-1",
                is_gm=False,
                reaction_opportunity_id="op-1",
                slot_level=1,
                actor_participant_id="caster",
                override_resource_limit=False,
            )

        self.assertEqual(result["applied_damage"], 13)
        self.assertTrue(result["reaction_consumed"])
        self.assertTrue(result["slot_consumed"])
        self.assertEqual(actor_model.state_json["spellcasting"]["slots"]["1"]["used"], 1)
        self.assertEqual(len(state.reaction_opportunities), 1)
        self.assertEqual(state.reaction_opportunities[0]["status"], "used")

    async def test_hellish_rebuke_rejects_missing_opportunity_without_consuming_resources(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=2,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster",
                    "ref_id": "caster-ref",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "actor_user_id": "user-1",
                    "turn_resources": {"reaction_used": False},
                    "active_effects": [],
                }
            ],
            reaction_opportunities=[],
        )
        db = MagicMock()
        with patch.object(CombatService, "get_state", return_value=state):
            with self.assertRaises(Exception):
                await CombatService.resolve_hellish_rebuke_reaction(
                    db,
                    "session-1",
                    actor_user_id="user-1",
                    is_gm=False,
                    reaction_opportunity_id="missing",
                    slot_level=1,
                    actor_participant_id="caster",
                    override_resource_limit=False,
                )
        resources = CombatService._get_turn_resources(state.participants[0])
        self.assertFalse(resources.get("reaction_used"))

    async def test_hellish_rebuke_rejects_invalid_slot_without_consuming_reaction(self):
        state = CombatState(
            id="combat-1",
            session_id="session-1",
            phase=CombatPhase.active,
            round=2,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster",
                    "ref_id": "caster-ref",
                    "kind": "player",
                    "display_name": "Caster",
                    "status": "active",
                    "actor_user_id": "user-1",
                    "turn_resources": {"reaction_used": False},
                    "active_effects": [],
                },
                {
                    "id": "attacker",
                    "ref_id": "attacker-ref",
                    "kind": "session_entity",
                    "display_name": "Attacker",
                    "status": "active",
                    "active_effects": [],
                },
            ],
            reaction_opportunities=[
                {
                    "id": "op-1",
                    "kind": "damage_taken",
                    "spell_key": "hellish_rebuke",
                    "actor_participant_id": "caster",
                    "source_participant_id": "attacker",
                    "status": "available",
                }
            ],
        )
        db = MagicMock()
        with patch.object(CombatService, "get_state", return_value=state):
            with self.assertRaises(Exception):
                await CombatService.resolve_hellish_rebuke_reaction(
                    db,
                    "session-1",
                    actor_user_id="user-1",
                    is_gm=False,
                    reaction_opportunity_id="op-1",
                    slot_level=0,
                    actor_participant_id="caster",
                    override_resource_limit=False,
                )
        resources = CombatService._get_turn_resources(state.participants[0])
        self.assertFalse(resources.get("reaction_used"))
