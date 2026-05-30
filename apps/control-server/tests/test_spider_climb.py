from __future__ import annotations

import json
import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.routes.sessions.state import _cast_spell_out_of_combat_for_player
from app.models.combat import CombatPhase, CombatState
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.combat import CombatService, CombatServiceError
from app.services.combat_service.condition_effects_predicates import (
    has_spider_climb,
    resolve_climb_speed_mode,
)
from app.services.combat_service.spell_automation import CombatSpellAutomationMixin
from app.services.out_of_combat_cast import _is_ooc_utility_spell, build_persisted_effects
from app.services.spell_targeting_semantics import resolve_spell_targeting_semantics


class SpiderClimbSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "Base", "base_spells.seed.json"
        )
        with open(os.path.abspath(path), encoding="utf-8") as f:
            data = json.load(f)
        cls.entry = next((s for s in data.get("spells", []) if s.get("canonicalKey") == "spider_climb"), None)

    def test_contract(self):
        self.assertIsNotNone(self.entry)
        self.assertEqual(self.entry["level"], 2)
        self.assertEqual(self.entry["school"], "transmutation")
        self.assertIn("Sorcerer", self.entry["classesJson"])
        self.assertIn("Warlock", self.entry["classesJson"])
        self.assertIn("Wizard", self.entry["classesJson"])
        self.assertEqual(self.entry["castingTimeType"], "action")
        self.assertEqual(self.entry["rangeMeters"], 1.5)
        self.assertEqual(self.entry["durationSeconds"], 3600)
        self.assertTrue(self.entry["concentration"])
        self.assertEqual(self.entry["resolutionType"], "utility")
        self.assertEqual(self.entry["selectionType"], "creature")
        self.assertEqual(self.entry["attackType"], "none")
        self.assertTrue(self.entry.get("outOfCombatCastable"))
        self.assertEqual(self.entry.get("outOfCombatTarget"), "self_or_ally")


class SpiderClimbTargetingAndRegistryTests(unittest.TestCase):
    def test_targeting_override(self):
        sem = resolve_spell_targeting_semantics({"canonicalKey": "spider_climb"})
        self.assertEqual(sem.selection_type, "creature")
        self.assertEqual(sem.target_anchor, "selected_target")
        self.assertEqual(sem.attack_type, "none")
        self.assertEqual(sem.range_kind, "touch")
        self.assertEqual(sem.effect_timing, "persistent")

    def test_registry_entry(self):
        spec = CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY.get("spider_climb")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.default_mode, "utility")
        self.assertFalse(spec.requires_effect_payload)
        self.assertEqual(spec.handler_name, "_cast_spider_climb_automation")


class SpiderClimbCombatTests(unittest.IsolatedAsyncioTestCase):
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
                    "display_name": "Mago A",
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
                    "id": "ally-a",
                    "ref_id": "ally-a-ref",
                    "kind": "player",
                    "display_name": "Aliado A",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "u1",
                    "active_effects": [],
                },
                {
                    "id": "ally-b",
                    "ref_id": "ally-b-ref",
                    "kind": "player",
                    "display_name": "Aliado B",
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "u2",
                    "active_effects": [],
                },
            ],
        )

    async def test_requires_target_and_no_variant(self):
        st = self._state()
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_spider_climb_automation(
                MagicMock(), "s1", attacker=st.participants[0], attacker_model=MagicMock(),
                actor_user_id="ua", is_gm=False, req=SimpleNamespace(variant_key=None),
                state=st, spell_context={"spell_name": "Escalada de Aranha"}, target_participant=None,
            )
        with self.assertRaises(CombatServiceError):
            await CombatService._cast_spider_climb_automation(
                MagicMock(), "s1", attacker=st.participants[0], attacker_model=MagicMock(),
                actor_user_id="ua", is_gm=False, req=SimpleNamespace(variant_key="x"),
                state=st, spell_context={"spell_name": "Escalada de Aranha"}, target_participant=st.participants[2],
            )

    async def test_cross_target_concentration(self):
        st = self._state()
        caster = st.participants[0]
        ally_a = st.participants[2]
        ally_b = st.participants[3]
        ally_a["active_effects"] = [
            {
                "id": "old-a",
                "kind": "spell_effect",
                "source_participant_id": "caster-a",
                "metadata": {"source_spell_key": "spider_climb", "concentration": True, "concentration_group": "grp-old"},
            }
        ]

        with patch("app.services.combat_service.spells.automation._buffs_physical.get_game_time_seconds", return_value=100):
            await CombatService._cast_spider_climb_automation(
                MagicMock(), "s1", attacker=caster, attacker_model=MagicMock(), actor_user_id="ua", is_gm=False,
                req=SimpleNamespace(variant_key=None), state=st,
                spell_context={"spell_name": "Escalada de Aranha", "spell_canonical_key": "spider_climb", "spell_level": 2, "slot_level": 2},
                target_participant=ally_b,
            )

        self.assertEqual(
            len([e for e in ally_a["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "spider_climb"]),
            0,
        )
        b_effects = [e for e in ally_b["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "spider_climb"]
        self.assertEqual(len(b_effects), 1)
        md = b_effects[0]["metadata"]
        self.assertTrue(md["concentration"])
        self.assertTrue(md["concentration_group"])
        self.assertEqual(md["source_participant_id"], "caster-a")

    async def test_cross_caster_same_target_replaces(self):
        st = self._state()
        target = st.participants[2]
        target["active_effects"] = [
            {
                "id": "old-sc",
                "kind": "spell_effect",
                "source_participant_id": "caster-a",
                "metadata": {"source_spell_key": "spider_climb", "concentration": True, "concentration_group": "grp-a"},
            }
        ]

        with patch("app.services.combat_service.spells.automation._buffs_physical.get_game_time_seconds", return_value=120):
            await CombatService._cast_spider_climb_automation(
                MagicMock(), "s1", attacker=st.participants[1], attacker_model=MagicMock(), actor_user_id="ub", is_gm=False,
                req=SimpleNamespace(variant_key=None), state=st,
                spell_context={"spell_name": "Escalada de Aranha", "spell_canonical_key": "spider_climb", "spell_level": 2, "slot_level": 2},
                target_participant=target,
            )

        effects = [e for e in target["active_effects"] if (e.get("metadata") or {}).get("source_spell_key") == "spider_climb"]
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].get("source_participant_id"), "caster-b")
        self.assertEqual((effects[0].get("metadata") or {}).get("source_participant_id"), "caster-b")


class SpiderClimbOocTests(unittest.IsolatedAsyncioTestCase):
    def test_ooc_allowlist_and_persisted_shape(self):
        self.assertTrue(_is_ooc_utility_spell("spider_climb"))
        spell = SimpleNamespace(
            canonical_key="spider_climb",
            name_pt="Escalada de Aranha",
            name_en="Spider Climb",
            concentration=True,
            effects_json=None,
        )
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u2",
            variant_key=None,
            game_time_seconds=10,
        )
        self.assertEqual(len(effects), 1)
        md = effects[0]["metadata"]
        self.assertEqual(md["source_spell_key"], "spider_climb")
        self.assertTrue(md["concentration"])
        self.assertTrue(md["concentration_group"])
        self.assertFalse(md["prevents_fall_damage"])

    async def test_ooc_detect_magic_then_spider_on_ally_clears_old_concentration(self):
        entry = SimpleNamespace(campaign_id="camp-1", party_id="party-1")
        caster_state = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "slots": {"2": {"used": 0, "max": 1}},
                    "spells": [{"id": "spell-sc", "canonicalKey": "spider_climb", "level": 2, "prepared": True}],
                },
                "active_spell_effects": [
                    {
                        "id": "dm-old",
                        "kind": "spell_effect",
                        "metadata": {
                            "source_spell_key": "detect_magic",
                            "source_spell_name": "Detectar Magia",
                            "concentration": True,
                            "concentration_group": "grp-old",
                        },
                    }
                ],
            },
            updated_at=None,
            created_at=None,
        )
        ally_state = SimpleNamespace(state_json={}, updated_at=None, created_at=None)
        campaign_spell = SimpleNamespace(
            canonical_key="spider_climb",
            name_pt="Escalada de Aranha",
            name_en="Spider Climb",
            out_of_combat_castable=True,
            out_of_combat_target="self_or_ally",
            concentration=True,
            level=2,
            effects_json=None,
        )
        session = MagicMock()
        q1 = MagicMock(); q1.first.return_value = caster_state
        q2 = MagicMock(); q2.first.return_value = ally_state
        q3 = MagicMock(); q3.first.return_value = campaign_spell
        session.exec.side_effect = [q1, q2, q3]

        req = OutOfCombatCastRequest.model_validate(
            {"spellId": "spell-sc", "slotLevel": 2, "targetPlayerUserId": "ally-user"}
        )
        with (
            patch("app.api.routes.sessions.state.ensure_session_state", side_effect=[caster_state, ally_state]),
            patch("app.api.routes.sessions.state.check_out_of_combat_cast_eligibility", return_value=(True, None)),
            patch("app.api.routes.sessions.state.finalize_session_state_data", side_effect=lambda data, **_: data),
            patch("app.api.routes.sessions.state.get_game_time_seconds", return_value=200),
            patch("app.api.routes.sessions.state.clear_concentration_group_across_session", return_value=[]),
            patch("app.api.routes.sessions.state._resolve_ooc_activity_actor", return_value=(None, None)),
            patch("app.api.routes.sessions.state.flag_modified"),
            patch("app.api.routes.sessions.state.publish_state_update", new_callable=AsyncMock),
            patch("app.api.routes.sessions.state.to_state_read", side_effect=lambda s: s),
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

        caster_effect_keys = [
            (e.get("metadata") or {}).get("source_spell_key")
            for e in (caster_state.state_json.get("active_spell_effects") or [])
            if isinstance(e, dict)
        ]
        self.assertNotIn("detect_magic", caster_effect_keys)
        ally_spider = [
            e for e in (ally_state.state_json.get("active_spell_effects") or [])
            if (e.get("metadata") or {}).get("source_spell_key") == "spider_climb"
        ]
        self.assertEqual(len(ally_spider), 1)
        self.assertEqual(caster_state.state_json["spellcasting"]["slots"]["2"]["used"], 1)

    async def test_ooc_invalid_cast_does_not_consume_slot(self):
        entry = SimpleNamespace(campaign_id="camp-1", party_id="party-1")
        caster_state = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "slots": {"2": {"used": 0, "max": 1}},
                    "spells": [{"id": "spell-sc", "canonicalKey": "spider_climb", "level": 2, "prepared": True}],
                }
            },
            updated_at=None,
            created_at=None,
        )
        before = deepcopy(caster_state.state_json)
        campaign_spell = SimpleNamespace(
            canonical_key="spider_climb",
            name_pt="Escalada de Aranha",
            name_en="Spider Climb",
            out_of_combat_castable=True,
            out_of_combat_target="self_or_ally",
            concentration=True,
            level=2,
            effects_json=None,
        )
        session = MagicMock()
        q1 = MagicMock(); q1.first.return_value = caster_state
        q2 = MagicMock(); q2.first.return_value = campaign_spell
        session.exec.side_effect = [q1, q2]
        req = OutOfCombatCastRequest.model_validate({"spellId": "spell-sc", "slotLevel": 2})
        with (
            patch("app.api.routes.sessions.state.ensure_session_state", return_value=caster_state),
            patch("app.api.routes.sessions.state.check_out_of_combat_cast_eligibility", return_value=(False, "No spell slot of level 2 remaining")),
        ):
            with self.assertRaises(HTTPException):
                await _cast_spell_out_of_combat_for_player(
                    entry=entry,
                    session_id="session-1",
                    req=req,
                    actor_user=SimpleNamespace(id="u1"),
                    caster_user_id="u1",
                    session=session,
                    cast_by_gm=False,
                )
        self.assertEqual(caster_state.state_json, before)


class SpiderClimbMovementHelperTests(unittest.TestCase):
    def test_helpers(self):
        p = {"active_effects": []}
        self.assertFalse(has_spider_climb(p))
        mode = resolve_climb_speed_mode(p)
        self.assertFalse(mode["hasSpiderClimb"])
        self.assertFalse(mode["preventsFallDamage"])

        p2 = {
            "active_effects": [
                {"metadata": {"source_spell_key": "spider_climb"}},
                {"metadata": {"source_spell_key": "spider_climb"}},
            ]
        }
        self.assertTrue(has_spider_climb(p2))
        mode2 = resolve_climb_speed_mode(p2)
        self.assertTrue(mode2["hasSpiderClimb"])
        self.assertTrue(mode2["canMoveOnCeilings"])
        self.assertFalse(mode2["grantsFlight"])


if __name__ == "__main__":
    unittest.main()
