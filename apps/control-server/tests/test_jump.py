from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.services.ooc_spell_cast_service import (
    cast_spell_out_of_combat_for_player as _cast_spell_out_of_combat_for_player,
)
from app.models.combat import CombatPhase, CombatState
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.condition_effects_predicates import resolve_jump_distance_multiplier
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _is_ooc_utility_spell, build_persisted_effects
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


class JumpSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next((s for s in data.get("spells", []) if s.get("canonicalKey") == "jump"), None)

    def test_entry_exists_and_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 1)
        self.assertEqual(self.entry["school"], "transmutation")
        self.assertIn("Druid", self.entry["classesJson"])
        self.assertIn("Ranger", self.entry["classesJson"])
        self.assertIn("Sorcerer", self.entry["classesJson"])
        self.assertIn("Wizard", self.entry["classesJson"])
        self.assertEqual(self.entry["castingTimeType"], "action")
        self.assertEqual(self.entry["rangeMeters"], 1.5)
        self.assertEqual(self.entry["durationSeconds"], 60)
        self.assertFalse(self.entry["concentration"])
        self.assertFalse(self.entry["ritual"])
        self.assertEqual(self.entry["resolutionType"], "utility")
        self.assertEqual(self.entry["selectionType"], "creature")
        self.assertEqual(self.entry["attackType"], "none")
        self.assertTrue(self.entry.get("outOfCombatCastable"))
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")
        self.assertNotIn("damageDice", self.entry)
        self.assertNotIn("savingThrow", self.entry)


class JumpTargetingAndRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "jump"})
        self.assertEqual(sem.selection_type, "creature")
        self.assertEqual(sem.target_anchor, "selected_target")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "touch")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("jump")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_jump_automation")


class JumpCombatAutomationTests(unittest.IsolatedAsyncioTestCase):
    def _state(self) -> CombatState:
        return CombatState(
            id="c1",
            session_id="s1",
            phase=CombatPhase.active,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "caster-a",
                    "ref_id": "player-a",
                    "kind": "player",
                    "display_name": "Druida A",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "ua",
                    "active_effects": [],
                },
                {
                    "id": "caster-b",
                    "ref_id": "player-b",
                    "kind": "player",
                    "display_name": "Mago B",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "ub",
                    "active_effects": [],
                },
                {
                    "id": "target-1",
                    "ref_id": "ally-1",
                    "kind": "player",
                    "display_name": "Guerreiro",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "u1",
                    "active_effects": [],
                },
                {
                    "id": "target-2",
                    "ref_id": "ally-2",
                    "kind": "player",
                    "display_name": "Ladino",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "u2",
                    "active_effects": [],
                },
            ],
        )

    async def test_requires_target(self):
        state = self._state()
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_jump_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="ua",
                is_gm=False,
                req=SimpleNamespace(variant_key=None),
                state=state,
                spell_context={"spell_name": "Salto", "spell_canonical_key": "jump"},
                target_participant=None,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_variant_key_rejected(self):
        state = self._state()
        with self.assertRaises(CombatServiceError) as ctx:
            await CombatService._cast_jump_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="ua",
                is_gm=False,
                req=SimpleNamespace(variant_key="x"),
                state=state,
                spell_context={"spell_name": "Salto", "spell_canonical_key": "jump"},
                target_participant=state.participants[2],
            )
        self.assertEqual(ctx.exception.status_code, 400)

    async def test_recast_is_target_scoped_not_caster_scoped(self):
        state = self._state()
        target_1 = state.participants[2]
        target_2 = state.participants[3]
        target_1["active_effects"] = [
            {"id": "old-jump", "kind": "spell_effect", "metadata": {"source_spell_key": "jump", "jump_distance_multiplier": 3}},
            {"id": "other", "kind": "spell_effect", "metadata": {"source_spell_key": "bless"}},
        ]

        with patch("app.services.combat_service.spells.automation._buffs_physical.get_game_time_seconds", return_value=10):
            await CombatService._cast_jump_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[0],
                attacker_model=MagicMock(),
                actor_user_id="ua",
                is_gm=False,
                req=SimpleNamespace(variant_key=None),
                state=state,
                spell_context={"spell_name": "Salto", "spell_canonical_key": "jump", "spell_mode": "utility", "spell_level": 1, "slot_level": 1},
                target_participant=target_2,
            )

        # Jump preexistente no alvo 1 permanece intacto.
        self.assertEqual(
            len([e for e in target_1["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "jump"]),
            1,
        )
        # Alvo 2 recebeu Jump.
        target_2_jump = [e for e in target_2["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "jump"]
        self.assertEqual(len(target_2_jump), 1)

    async def test_recast_same_target_replaces_previous_even_other_caster(self):
        state = self._state()
        target_1 = state.participants[2]
        target_1["active_effects"] = [
            {
                "id": "old-jump",
                "kind": "spell_effect",
                "source_participant_id": "caster-a",
                "metadata": {"source_spell_key": "jump", "jump_distance_multiplier": 3},
            }
        ]

        with patch("app.services.combat_service.spells.automation._buffs_physical.get_game_time_seconds", return_value=20):
            await CombatService._cast_jump_automation(
                MagicMock(),
                "s1",
                attacker=state.participants[1],
                attacker_model=MagicMock(),
                actor_user_id="ub",
                is_gm=False,
                req=SimpleNamespace(variant_key=None),
                state=state,
                spell_context={"spell_name": "Salto", "spell_canonical_key": "jump", "spell_mode": "utility", "spell_level": 1, "slot_level": 1},
                target_participant=target_1,
            )

        jump_effects = [e for e in target_1["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "jump"]
        self.assertEqual(len(jump_effects), 1)
        self.assertEqual(jump_effects[0].get("source_participant_id"), "caster-b")
        metadata = jump_effects[0]["metadata"]
        self.assertEqual(metadata["jump_distance_multiplier"], 3)
        self.assertFalse(metadata["grants_extra_movement"])
        self.assertFalse(metadata["grants_flight"])
        self.assertFalse(metadata["prevents_fall_damage"])


class JumpOocTests(unittest.IsolatedAsyncioTestCase):
    def test_jump_in_special_ooc_utility_spells(self):
        self.assertTrue(_is_ooc_utility_spell("jump"))

    def test_build_persisted_effects_jump(self):
        spell = SimpleNamespace(
            canonical_key="jump",
            name_pt="Salto",
            name_en="Jump",
            concentration=False,
            effects_json=None,
        )
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key=None,
            game_time_seconds=100,
        )
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        self.assertEqual(effect["duration_type"], "timed")
        self.assertEqual(effect["expires_at_game_time_seconds"], 160)
        md = effect["metadata"]
        self.assertEqual(md["source_spell_key"], "jump")
        self.assertEqual(md["jump_distance_multiplier"], 3)
        self.assertFalse(md["grants_extra_movement"])
        self.assertFalse(md["grants_flight"])
        self.assertFalse(md["prevents_fall_damage"])

    async def test_ooc_valid_consumes_slot_and_invalid_does_not(self):
        entry = SimpleNamespace(campaign_id="camp-1", party_id="party-1")
        caster_state = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "slots": {"1": {"used": 0, "max": 1}},
                    "spells": [{"id": "spell-jump", "canonicalKey": "jump", "level": 1, "prepared": True}],
                }
            },
            updated_at=None,
            created_at=None,
        )
        campaign_spell = SimpleNamespace(
            canonical_key="jump",
            name_pt="Salto",
            name_en="Jump",
            out_of_combat_castable=True,
            out_of_combat_target="self_or_ally",
            concentration=False,
            level=1,
            effects_json=None,
        )

        session_valid = MagicMock()
        q1 = MagicMock(); q1.first.return_value = caster_state
        q2 = MagicMock(); q2.first.return_value = campaign_spell
        session_valid.exec.side_effect = [q1, q2]

        req_valid = OutOfCombatCastRequest.model_validate({"spellId": "spell-jump", "slotLevel": 1})
        with (
            patch("app.services.ooc_spell_cast_service.ensure_session_state", return_value=caster_state),
            patch("app.services.ooc_spell_cast_service.check_out_of_combat_cast_eligibility", return_value=(True, None)),
            patch("app.services.ooc_spell_cast_service.finalize_session_state_data", side_effect=lambda data, **_: data),
            patch("app.services.ooc_spell_cast_service.get_game_time_seconds", return_value=200),
            patch("app.services.ooc_spell_cast_service._resolve_ooc_activity_actor", return_value=(None, None)),
            patch("app.services.ooc_spell_cast_service.flag_modified"),
            patch("app.services.ooc_spell_cast_service.publish_state_update", new_callable=AsyncMock),
            patch("app.services.ooc_spell_cast_service.to_state_read", side_effect=lambda s: s),
        ):
            await _cast_spell_out_of_combat_for_player(
                entry=entry,
                session_id="session-1",
                req=req_valid,
                actor_user=SimpleNamespace(id="u1"),
                caster_user_id="u1",
                session=session_valid,
                cast_by_gm=False,
            )
        self.assertEqual(caster_state.state_json["spellcasting"]["slots"]["1"]["used"], 1)

        # invalid cast keeps slots unchanged
        caster_state_invalid = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "slots": {"1": {"used": 0, "max": 1}},
                    "spells": [{"id": "spell-jump", "canonicalKey": "jump", "level": 1, "prepared": True}],
                }
            },
            updated_at=None,
            created_at=None,
        )
        before = deepcopy(caster_state_invalid.state_json)
        session_invalid = MagicMock()
        qi1 = MagicMock(); qi1.first.return_value = caster_state_invalid
        qi2 = MagicMock(); qi2.first.return_value = campaign_spell
        session_invalid.exec.side_effect = [qi1, qi2]
        req_invalid = OutOfCombatCastRequest.model_validate({"spellId": "spell-jump", "slotLevel": 1})
        with (
            patch("app.services.ooc_spell_cast_service.ensure_session_state", return_value=caster_state_invalid),
            patch("app.services.ooc_spell_cast_service.check_out_of_combat_cast_eligibility", return_value=(False, "No spell slot of level 1 remaining")),
        ):
            with self.assertRaises(HTTPException):
                await _cast_spell_out_of_combat_for_player(
                    entry=entry,
                    session_id="session-1",
                    req=req_invalid,
                    actor_user=SimpleNamespace(id="u1"),
                    caster_user_id="u1",
                    session=session_invalid,
                    cast_by_gm=False,
                )
        self.assertEqual(caster_state_invalid.state_json, before)

    async def test_ooc_recast_replaces_only_target_jump(self):
        entry = SimpleNamespace(campaign_id="camp-1", party_id="party-1")
        caster_state = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "slots": {"1": {"used": 0, "max": 2}},
                    "spells": [{"id": "spell-jump", "canonicalKey": "jump", "level": 1, "prepared": True}],
                },
                "active_spell_effects": [
                    {"id": "caster-jump", "kind": "spell_effect", "metadata": {"source_spell_key": "jump"}},
                ],
            },
            updated_at=None,
            created_at=None,
        )
        target_state = SimpleNamespace(
            state_json={
                "active_spell_effects": [
                    {"id": "target-jump-old", "kind": "spell_effect", "metadata": {"source_spell_key": "jump"}},
                    {"id": "target-bless", "kind": "spell_effect", "metadata": {"source_spell_key": "bless"}},
                ]
            },
            updated_at=None,
            created_at=None,
        )
        campaign_spell = SimpleNamespace(
            canonical_key="jump",
            name_pt="Salto",
            name_en="Jump",
            out_of_combat_castable=True,
            out_of_combat_target="self_or_ally",
            concentration=False,
            level=1,
            effects_json=None,
        )
        session = MagicMock()
        q1 = MagicMock(); q1.first.return_value = caster_state
        q2 = MagicMock(); q2.first.return_value = target_state
        q3 = MagicMock(); q3.first.return_value = campaign_spell
        session.exec.side_effect = [q1, q2, q3]

        req = OutOfCombatCastRequest.model_validate(
            {"spellId": "spell-jump", "slotLevel": 1, "targetPlayerUserId": "ally-1"}
        )
        with (
            patch("app.services.ooc_spell_cast_service.ensure_session_state", side_effect=[caster_state, target_state]),
            patch("app.services.ooc_spell_cast_service.check_out_of_combat_cast_eligibility", return_value=(True, None)),
            patch("app.services.ooc_spell_cast_service.finalize_session_state_data", side_effect=lambda data, **_: data),
            patch("app.services.ooc_spell_cast_service.get_game_time_seconds", return_value=300),
            patch("app.services.ooc_spell_cast_service._resolve_ooc_activity_actor", return_value=(None, None)),
            patch("app.services.ooc_spell_cast_service.flag_modified"),
            patch("app.services.ooc_spell_cast_service.publish_state_update", new_callable=AsyncMock),
            patch("app.services.ooc_spell_cast_service.to_state_read", side_effect=lambda s: s),
        ):
            await _cast_spell_out_of_combat_for_player(
                entry=entry,
                session_id="session-1",
                req=req,
                actor_user=SimpleNamespace(id="u1"),
                caster_user_id="u1",
                session=session,
                cast_by_gm=False,
            )

        caster_jump_count = sum(
            1
            for e in (caster_state.state_json.get("active_spell_effects") or [])
            if (e.get("metadata") or {}).get("source_spell_key") == "jump"
        )
        target_jump_count = sum(
            1
            for e in (target_state.state_json.get("active_spell_effects") or [])
            if (e.get("metadata") or {}).get("source_spell_key") == "jump"
        )
        target_bless_count = sum(
            1
            for e in (target_state.state_json.get("active_spell_effects") or [])
            if (e.get("metadata") or {}).get("source_spell_key") == "bless"
        )
        self.assertEqual(caster_jump_count, 1)
        self.assertEqual(target_jump_count, 1)
        self.assertEqual(target_bless_count, 1)


class JumpMovementHelperTests(unittest.TestCase):
    def test_resolve_jump_distance_multiplier(self):
        self.assertEqual(resolve_jump_distance_multiplier({"active_effects": []}), 1)
        self.assertEqual(
            resolve_jump_distance_multiplier(
                {
                    "active_effects": [
                        {"metadata": {"source_spell_key": "jump", "jump_distance_multiplier": 3}},
                    ]
                }
            ),
            3,
        )
        self.assertEqual(
            resolve_jump_distance_multiplier(
                {
                    "active_effects": [
                        {"metadata": {"source_spell_key": "jump", "jump_distance_multiplier": 3}},
                        {"metadata": {"source_spell_key": "jump", "jump_distance_multiplier": 3}},
                    ]
                }
            ),
            3,
        )


if __name__ == "__main__":
    unittest.main()
