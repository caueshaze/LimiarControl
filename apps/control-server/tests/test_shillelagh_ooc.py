from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.sessions.state import _cast_spell_out_of_combat_for_player
from app.schemas.session_state import OutOfCombatCastRequest
from app.services.out_of_combat_cast import _is_ooc_utility_spell, build_persisted_effects


class ShillelaghOocSchemaTests(unittest.TestCase):
    def test_accepts_weapon_item_id_camel(self):
        req = OutOfCombatCastRequest.model_validate(
            {
                "spellId": "spell-1",
                "weaponItemId": "item-abc",
            }
        )
        self.assertEqual(req.weapon_item_id, "item-abc")

    def test_accepts_weapon_item_id_snake(self):
        req = OutOfCombatCastRequest.model_validate(
            {
                "spellId": "spell-1",
                "weapon_item_id": "item-abc",
            }
        )
        self.assertEqual(req.weapon_item_id, "item-abc")


class ShillelaghOocServiceTests(unittest.TestCase):
    def test_shillelagh_in_special_ooc_utility_spells(self):
        self.assertTrue(_is_ooc_utility_spell("shillelagh"))

    def test_build_persisted_effects_shillelagh_returns_timed_effect(self):
        spell = SimpleNamespace(
            canonical_key="shillelagh",
            name_pt="Bordão Místico",
            name_en="Shillelagh",
            concentration=False,
            effects_json=None,
        )
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=100,
            weapon_item_id="inv-1",
            weapon_canonical_key="quarterstaff",
            weapon_name="Bordão",
        )
        self.assertEqual(len(effects), 1)
        effect = effects[0]
        self.assertEqual(effect["duration_type"], "timed")
        self.assertEqual(effect["created_at_game_time_seconds"], 100)
        self.assertEqual(effect["expires_at_game_time_seconds"], 160)
        metadata = effect["metadata"]
        self.assertEqual(metadata["source_spell_key"], "shillelagh")
        self.assertEqual(metadata["weapon_item_id"], "inv-1")
        self.assertEqual(metadata["weapon_key"], "quarterstaff")
        self.assertEqual(metadata["override_damage_die"], "1d8")
        self.assertTrue(metadata["damage_counts_as_magical"])

    def test_build_persisted_effects_shillelagh_requires_weapon_context(self):
        spell = SimpleNamespace(
            canonical_key="shillelagh",
            name_pt="Bordão Místico",
            name_en="Shillelagh",
            concentration=False,
            effects_json=None,
        )
        effects = build_persisted_effects(
            spell=spell,
            caster_user_id="u1",
            target_user_id="u1",
            variant_key=None,
            game_time_seconds=100,
            weapon_item_id=None,
            weapon_canonical_key=None,
            weapon_name=None,
        )
        self.assertEqual(effects, [])


class ShillelaghOocRouteGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_spell_id_and_canonical_key_divergence_returns_400(self):
        state = SimpleNamespace(
            state_json={
                "spellcasting": {
                    "spells": [
                        {"id": "spell-cw", "canonicalKey": "cure_wounds", "level": 1, "prepared": True},
                        {"id": "spell-sh", "canonicalKey": "shillelagh", "level": 0, "prepared": True},
                    ]
                }
            },
            updated_at=None,
            created_at=None,
        )
        entry = SimpleNamespace(campaign_id="camp-1", party_id=None)
        session = MagicMock()
        session.exec.return_value.first.return_value = state
        req = OutOfCombatCastRequest.model_validate(
            {
                "spellId": "spell-cw",
                "canonicalKey": "shillelagh",
            }
        )

        with patch("app.api.routes.sessions.state.ensure_session_state", return_value=state):
            with self.assertRaises(HTTPException) as ctx:
                await _cast_spell_out_of_combat_for_player(
                    entry=entry,
                    session_id="session-1",
                    req=req,
                    actor_user=SimpleNamespace(id="u1"),
                    caster_user_id="u1",
                    session=session,
                    cast_by_gm=False,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("spellId and canonicalKey refer to different spells", str(ctx.exception.detail))


if __name__ == "__main__":
    unittest.main()
