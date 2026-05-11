from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat_spells import CombatResolveSpellContextRequest
from app.services.combat import CombatService, CombatServiceError


def _make_participant(pid: str, ref_id: str, team: str = "enemies", kind: str = "session_entity") -> dict:
    return {
        "id": pid,
        "ref_id": ref_id,
        "kind": kind,
        "display_name": f"Target {pid}",
        "initiative": 5,
        "status": "active",
        "team": team,
        "visible": True,
        "actor_user_id": None,
        "active_effects": [],
        "turn_resources": {"action_used": False, "bonus_action_used": False, "reaction_used": False},
    }


def _make_player() -> dict:
    return {
        "id": "p1",
        "ref_id": "caster",
        "kind": "player",
        "display_name": "Caster",
        "initiative": 10,
        "status": "active",
        "team": "players",
        "visible": True,
        "actor_user_id": "u1",
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


def _make_hold_person_catalog_spell(max_targets: int = 1):
    return SimpleNamespace(
        canonical_key="hold_person",
        name_en="Hold Person",
        name_pt="Hold Person",
        level=2,
        resolution_type="control",
        damage_dice="1d1",
        heal_dice=None,
        damage_type="psychic",
        saving_throw="wisdom",
        save_success_outcome="none",
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
        range_meters=18,
        duration="Concentration, up to 1 minute",
        concentration=True,
        cover_applies_to_save="none",
        max_targets=max_targets,
        requires_target_sight=True,
        requires_target_effect=True,
        requires_point_sight=False,
        requires_point_effect=False,
        effects_json=[{"type": "apply_condition", "params": {"condition": "paralyzed"}}],
    )


class HoldPersonUpcastMultiTargetTests(unittest.TestCase):
    def _resolve_context(self, slot_level: int) -> dict:
        state = _make_state([_make_player()])
        attacker_state = SessionState(
            id="ss-1",
            session_id="s1",
            player_user_id="u1",
            state_json={
                "spellcasting": {
                    "spells": [{"canonicalKey": "hold_person", "level": 2, "prepared": True}],
                    "slots": {str(slot_level): {"used": 0, "max": 3}},
                }
            },
        )
        with (
            patch("app.services.combat.CombatService.get_state", return_value=state),
            patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session", return_value=_make_hold_person_catalog_spell(1)),
            patch("app.services.combat.CombatService._get_stats", return_value=(attacker_state, 12, 10, 10, 3, 4)),
        ):
            return CombatService.resolve_spell_context(
                MagicMock(),
                "s1",
                CombatResolveSpellContextRequest(
                    actor_participant_id="p1",
                    spell_canonical_key="hold_person",
                    spell_mode="saving_throw",
                    slot_level=slot_level,
                ),
                "u1",
                False,
            )

    def test_upcast_max_targets_progression(self):
        self.assertEqual(self._resolve_context(2)["max_targets"], 1)
        self.assertEqual(self._resolve_context(3)["max_targets"], 2)
        self.assertEqual(self._resolve_context(4)["max_targets"], 3)
        self.assertEqual(self._resolve_context(5)["max_targets"], 4)

    def test_slot_4_with_two_targets_is_valid(self):
        state = _make_state([_make_player(), _make_participant("e1", "enemy-1"), _make_participant("e2", "enemy-2")])
        req = SimpleNamespace(
            target_ref_ids=["enemy-1", "enemy-2"],
            target_ref_id=None,
            target_variant_assignments=None,
            effect_instance_targets=None,
        )
        resolved = CombatService._validate_plain_multi_target_refs(
            req=req,
            spell_context={"max_targets": 3, "spell_canonical_key": "hold_person"},
            state=state,
        )
        self.assertIsNotNone(resolved)
        self.assertEqual(len(resolved), 2)

    def test_slot_3_with_three_targets_fails(self):
        state = _make_state(
            [
                _make_player(),
                _make_participant("e1", "enemy-1"),
                _make_participant("e2", "enemy-2"),
                _make_participant("e3", "enemy-3"),
            ]
        )
        req = SimpleNamespace(
            target_ref_ids=["enemy-1", "enemy-2", "enemy-3"],
            target_ref_id=None,
            target_variant_assignments=None,
            effect_instance_targets=None,
        )
        with self.assertRaises(CombatServiceError):
            CombatService._validate_plain_multi_target_refs(
                req=req,
                spell_context={"max_targets": 2, "spell_canonical_key": "hold_person"},
                state=state,
            )


if __name__ == "__main__":
    unittest.main()
