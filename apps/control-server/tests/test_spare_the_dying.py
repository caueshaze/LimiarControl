from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


_SEED_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json")
)


def _load_seed_entry():
    with open(_SEED_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    spells = payload["spells"] if isinstance(payload, dict) else payload
    return next(
        (s for s in spells if isinstance(s, dict) and s.get("canonicalKey") == "spare_the_dying"),
        None,
    )


def _make_caster(pid: str = "caster", user_id: str = "u1") -> dict:
    return {
        "id": pid,
        "ref_id": pid,
        "kind": "player",
        "display_name": "Cleric",
        "status": "active",
        "team": "players",
        "actor_user_id": user_id,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_player_target(
    pid: str = "target",
    ref_id: str = "player-target",
    status: str = "downed",
    effects: list[dict] | None = None,
) -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": "player",
        "display_name": "Fallen Ally",
        "status": status,
        "team": "players",
        "actor_user_id": "u2",
        "active_effects": effects if effects is not None else [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_npc_target(
    pid: str = "npc-1",
    ref_id: str = "entity-1",
    status: str = "defeated",
) -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": "session_entity",
        "display_name": "Fallen NPC",
        "status": status,
        "team": "allies",
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


def _spell_context() -> dict:
    return {
        "spell_name": "Poupar os Moribundos",
        "spell_canonical_key": "spare_the_dying",
        "spell_mode": "utility",
        "concentration": False,
    }


def _downed_player_state(
    current_hp: int = 0,
    max_hp: int = 12,
    successes: int = 1,
    failures: int = 1,
) -> SessionState:
    return SessionState(
        id="ss-target",
        session_id="s1",
        player_user_id="player-target",
        state_json={
            "currentHP": current_hp,
            "maxHP": max_hp,
            "deathSaves": {"successes": successes, "failures": failures},
        },
    )


class SpareTheDyingSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = _load_seed_entry()

    def test_entry_exists(self):
        self.assertIsNotNone(self.entry, "spare_the_dying not found in seed")

    def test_level_is_0(self):
        self.assertEqual(self.entry["level"], 0)

    def test_school_is_necromancy(self):
        self.assertEqual(self.entry["school"], "necromancy")

    def test_classes_includes_cleric(self):
        self.assertIn("Cleric", self.entry["classesJson"])

    def test_range_meters(self):
        self.assertEqual(self.entry["rangeMeters"], 1.5)

    def test_range_kind(self):
        self.assertEqual(self.entry["rangeKind"], "touch")

    def test_resolution_type(self):
        self.assertEqual(self.entry["resolutionType"], "utility")

    def test_attack_type(self):
        self.assertEqual(self.entry["attackType"], "none")

    def test_no_concentration(self):
        self.assertFalse(self.entry["concentration"])

    def test_no_ritual(self):
        self.assertFalse(self.entry["ritual"])

    def test_no_damage_dice(self):
        self.assertNotIn("damageDice", self.entry)

    def test_no_damage_type(self):
        self.assertNotIn("damageType", self.entry)

    def test_no_saving_throw(self):
        self.assertNotIn("savingThrow", self.entry)

    def test_no_cantrip_scaling(self):
        self.assertNotIn("cantripScaling", self.entry)

    def test_no_upcast(self):
        self.assertNotIn("upcast", self.entry)

    def test_target_type_touch(self):
        self.assertEqual(self.entry["targetType"], "touch")

    def test_selection_type_creature(self):
        self.assertEqual(self.entry["selectionType"], "creature")

    def test_duration_instantaneous(self):
        self.assertEqual(self.entry["duration"], "Instantaneous")


class SpareTheDyingTargetingTests(unittest.TestCase):
    def test_override_exists(self):
        semantics = resolve_spell_targeting_semantics({"canonicalKey": "spare_the_dying"})
        self.assertEqual(semantics.selection_type, "creature")
        self.assertEqual(semantics.origin_type, "caster")
        self.assertEqual(semantics.target_anchor, "selected_target")
        self.assertEqual(semantics.attack_type, "none")
        self.assertEqual(semantics.range_kind, "touch")
        self.assertEqual(semantics.effect_timing, "immediate")


class SpareTheDyingRegistryTests(unittest.TestCase):
    def test_registered_in_automation_registry(self):
        registry = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY
        self.assertIn("spare_the_dying", registry)

    def test_default_mode_utility(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spare_the_dying"]
        self.assertEqual(spec.default_mode, "utility")

    def test_no_effect_payload_required(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spare_the_dying"]
        self.assertFalse(spec.requires_effect_payload)

    def test_handler_name(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY["spare_the_dying"]
        self.assertEqual(spec.handler_name, "_cast_spare_the_dying_automation")


class SpareTheDyingCastSuccessPlayerTests(unittest.IsolatedAsyncioTestCase):
    async def test_downed_player_stabilized(self):
        state = _make_state([_make_caster(), _make_player_target()])
        caster = state.participants[0]
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            result = await CombatService._cast_spare_the_dying_automation(
                MagicMock(),
                "s1",
                attacker=caster,
                attacker_model=MagicMock(),
                actor_user_id="u1",
                is_gm=False,
                req=req,
                state=state,
                spell_context=_spell_context(),
                target_participant=target,
            )

        self.assertTrue(result["stabilized"])
        self.assertEqual(result["healing"], 0)
        self.assertEqual(result["target_hp_after"], 0)
        self.assertEqual(result["action_kind"], "utility")

    async def test_hp_remains_zero(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        data = target_model.state_json
        self.assertEqual(data["currentHP"], 0)

    async def test_death_saves_set_to_stable(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state(successes=1, failures=2)

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        data = target_model.state_json
        self.assertEqual(data["deathSaves"]["successes"], 3)
        self.assertEqual(data["deathSaves"]["failures"], 0)

    async def test_status_becomes_stable(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target["status"], "stable")

    async def test_no_healing_event(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            result = await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(result["healing"], 0)
        self.assertEqual(result["damage"], 0)
        self.assertIsNone(result["is_hit"])
        self.assertIsNone(result["is_saved"])

    async def test_no_active_effect_created(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        initial_effects = list(target.get("active_effects", []))
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target.get("active_effects", []), initial_effects)

    async def test_summary_and_log_mention_stabilization(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            result = await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertIn("estabilizado", result["summary_text"])
        self.assertIn("estabilizando", result["__log_message"])

    async def test_already_stable_is_idempotent(self):
        state = _make_state([_make_caster(), _make_player_target(status="stable")])
        target = state.participants[1]
        target_model = _downed_player_state(successes=3, failures=0)

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            result = await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertTrue(result["stabilized"])
        self.assertEqual(target["status"], "stable")


class SpareTheDyingConditionPreservationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unconscious_condition_preserved(self):
        effects = [
            {"id": "eff-1", "kind": "condition", "condition_type": "unconscious",
             "source_participant_id": "system", "duration_type": "indefinite",
             "metadata": {"condition_type": "unconscious"}},
        ]
        state = _make_state([_make_caster(), _make_player_target(effects=effects)])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        unconscious = [e for e in target["active_effects"] if e.get("condition_type") == "unconscious"]
        self.assertEqual(len(unconscious), 1)

    async def test_prone_condition_preserved(self):
        effects = [
            {"id": "eff-2", "kind": "condition", "condition_type": "prone",
             "source_participant_id": "system", "duration_type": "indefinite",
             "metadata": {"condition_type": "prone"}},
        ]
        state = _make_state([_make_caster(), _make_player_target(effects=effects)])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        prone = [e for e in target["active_effects"] if e.get("condition_type") == "prone"]
        self.assertEqual(len(prone), 1)

    async def test_incapacitated_condition_preserved(self):
        effects = [
            {"id": "eff-3", "kind": "condition", "condition_type": "incapacitated",
             "source_participant_id": "system", "duration_type": "indefinite",
             "metadata": {"condition_type": "incapacitated"}},
        ]
        state = _make_state([_make_caster(), _make_player_target(effects=effects)])
        target = state.participants[1]
        target_model = _downed_player_state()

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        incap = [e for e in target["active_effects"] if e.get("condition_type") == "incapacitated"]
        self.assertEqual(len(incap), 1)


class SpareTheDyingNpcCastTests(unittest.IsolatedAsyncioTestCase):
    async def test_defeated_npc_becomes_stable(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]
        target_model = MagicMock()
        target_model.current_hp = 0

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            result = await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target["status"], "stable")
        self.assertTrue(result["stabilized"])
        self.assertEqual(result["target_hp_after"], 0)

    async def test_npc_hp_remains_zero(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]
        target_model = MagicMock()
        target_model.current_hp = 0

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target_model.current_hp, 0)

    async def test_npc_no_active_effect_created(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]
        target_model = MagicMock()
        target_model.current_hp = 0

        req = MagicMock()
        req.variant_key = None

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target.get("active_effects", []), [])


class SpareTheDyingCastInvalidTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_target_returns_400(self):
        state = _make_state([_make_caster()])
        req = MagicMock()
        req.variant_key = None

        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=None,
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_target_with_hp_above_zero_returns_400(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state(current_hp=5)

        req = MagicMock()
        req.variant_key = None

        hp_before = target_model.state_json["currentHP"]
        status_before = target["status"]

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService._cast_spare_the_dying_automation(
                    MagicMock(), "s1",
                    attacker=state.participants[0], attacker_model=MagicMock(),
                    actor_user_id="u1", is_gm=False, req=req, state=state,
                    spell_context=_spell_context(), target_participant=target,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("0 HP", str(ctx.exception))
        self.assertEqual(target_model.state_json["currentHP"], hp_before)
        self.assertEqual(target["status"], status_before)

    async def test_dead_target_returns_400(self):
        state = _make_state([_make_caster(), _make_player_target(status="dead")])
        target = state.participants[1]
        target_model = _downed_player_state(successes=0, failures=3)

        req = MagicMock()
        req.variant_key = None

        status_before = target["status"]
        saves_before = dict(target_model.state_json.get("deathSaves", {}))

        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("mortas", str(ctx.exception))
        self.assertEqual(target["status"], status_before)
        self.assertEqual(target_model.state_json["deathSaves"]["failures"], saves_before.get("failures", 3))

    async def test_variant_key_returns_400(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]

        req = MagicMock()
        req.variant_key = "something"

        status_before = target["status"]

        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("variantes", str(ctx.exception))
        self.assertEqual(target["status"], status_before)

    async def test_npc_with_hp_above_zero_returns_400(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]
        target_model = MagicMock()
        target_model.current_hp = 10

        req = MagicMock()
        req.variant_key = None

        status_before = target["status"]

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            with self.assertRaises(CombatServiceError) as ctx:
                await CombatService._cast_spare_the_dying_automation(
                    MagicMock(), "s1",
                    attacker=state.participants[0], attacker_model=MagicMock(),
                    actor_user_id="u1", is_gm=False, req=req, state=state,
                    spell_context=_spell_context(), target_participant=target,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(target["status"], status_before)


class SpareTheDyingCreatureTypeTests(unittest.IsolatedAsyncioTestCase):
    async def test_undead_rejected(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value="undead"
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_spell_automation_target(
                    MagicMock(), "s1",
                    spell_canonical_key="spare_the_dying",
                    target_participant=target,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("mortos-vivos", str(ctx.exception))

    async def test_construct_rejected(self):
        state = _make_state([_make_caster(), _make_npc_target()])
        target = state.participants[1]

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value="construct"
        ):
            with self.assertRaises(CombatServiceError) as ctx:
                CombatService._validate_spell_automation_target(
                    MagicMock(), "s1",
                    spell_canonical_key="spare_the_dying",
                    target_participant=target,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("constructos", str(ctx.exception))

    async def test_none_creature_type_allowed(self):
        target = _make_npc_target()

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value=None
        ):
            CombatService._validate_spell_automation_target(
                MagicMock(), "s1",
                spell_canonical_key="spare_the_dying",
                target_participant=target,
            )

    async def test_humanoid_allowed(self):
        target = _make_npc_target()

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value="humanoid"
        ):
            CombatService._validate_spell_automation_target(
                MagicMock(), "s1",
                spell_canonical_key="spare_the_dying",
                target_participant=target,
            )

    async def test_beast_allowed(self):
        target = _make_npc_target()

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value="beast"
        ):
            CombatService._validate_spell_automation_target(
                MagicMock(), "s1",
                spell_canonical_key="spare_the_dying",
                target_participant=target,
            )

    async def test_dragon_allowed(self):
        target = _make_npc_target()

        with patch.object(
            CombatService, "resolve_effective_creature_type", return_value="dragon"
        ):
            CombatService._validate_spell_automation_target(
                MagicMock(), "s1",
                spell_canonical_key="spare_the_dying",
                target_participant=target,
            )


class SpareTheDyingResourceSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_cantrip_not_in_seed_level0(self):
        entry = _load_seed_entry()
        self.assertEqual(entry["level"], 0)

    async def test_invalid_cast_does_not_mutate_player_state(self):
        state = _make_state([_make_caster(), _make_player_target()])
        target = state.participants[1]
        target_model = _downed_player_state(current_hp=5)

        req = MagicMock()
        req.variant_key = None

        hp_before = target_model.state_json["currentHP"]
        saves_before = dict(target_model.state_json["deathSaves"])
        status_before = target["status"]

        with patch.object(CombatService, "_get_stats", return_value=(target_model, 10, 10, 10, 2, 3)):
            with self.assertRaises(CombatServiceError):
                await CombatService._cast_spare_the_dying_automation(
                    MagicMock(), "s1",
                    attacker=state.participants[0], attacker_model=MagicMock(),
                    actor_user_id="u1", is_gm=False, req=req, state=state,
                    spell_context=_spell_context(), target_participant=target,
                )

        self.assertEqual(target_model.state_json["currentHP"], hp_before)
        self.assertEqual(target_model.state_json["deathSaves"], saves_before)
        self.assertEqual(target["status"], status_before)

    async def test_invalid_cast_does_not_add_active_effects(self):
        state = _make_state([_make_caster(), _make_player_target(status="dead")])
        target = state.participants[1]

        req = MagicMock()
        req.variant_key = None

        effects_before = list(target.get("active_effects", []))

        with self.assertRaises(CombatServiceError):
            await CombatService._cast_spare_the_dying_automation(
                MagicMock(), "s1",
                attacker=state.participants[0], attacker_model=MagicMock(),
                actor_user_id="u1", is_gm=False, req=req, state=state,
                spell_context=_spell_context(), target_participant=target,
            )

        self.assertEqual(target.get("active_effects", []), effects_before)


if __name__ == "__main__":
    unittest.main()
