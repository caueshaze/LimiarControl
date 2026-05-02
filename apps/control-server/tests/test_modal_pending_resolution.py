from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.combat import CombatPhase, CombatState
from app.models.session_state import SessionState
from app.schemas.combat import CombatResolveSaveRequest, CombatResolveSpellEffectRequest
from app.schemas.roll import RollResult
from app.services.combat import CombatService, CombatServiceError


def _build_state() -> CombatState:
    return CombatState(
        id="combat-modal-pending",
        session_id="session-modal-pending",
        phase=CombatPhase.active,
        round=1,
        current_turn_index=0,
        participants=[
            {
                "id": "p1",
                "ref_id": "player-1",
                "kind": "player",
                "display_name": "Mage",
                "initiative": 15,
                "status": "active",
                "team": "players",
                "visible": True,
                "actor_user_id": "user-1",
                "active_effects": [],
            },
            {
                "id": "e1",
                "ref_id": "enemy-1",
                "kind": "session_entity",
                "display_name": "Target A",
                "initiative": 10,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": [],
            },
            {
                "id": "e2",
                "ref_id": "enemy-2",
                "kind": "session_entity",
                "display_name": "Target B",
                "initiative": 8,
                "status": "active",
                "team": "enemies",
                "visible": True,
                "actor_user_id": None,
                "active_effects": [],
            },
        ],
    )


def _attacker_state() -> SessionState:
    return SessionState(
        id="state-1",
        session_id="session-modal-pending",
        player_user_id="user-1",
        state_json={
            "wildShape": {"active": False},
            "spellcasting": {"slots": {"1": {"used": 0, "max": 4}}},
        },
    )


def _manual_notes() -> list[dict]:
    return [
        {
            "target_participant_id": "e1",
            "target_ref_id": "enemy-1",
            "target_display_name": "Target A",
            "variant_key": "bears_endurance",
            "variant_label": "Resistência do Urso",
            "manual_notes": [
                {
                    "key": "grant_temp_hp",
                    "label": "PV temporários",
                    "description": "Conceda 2d6 PV temporários manualmente.",
                }
            ],
        },
        {
            "target_participant_id": "e2",
            "target_ref_id": "enemy-2",
            "target_display_name": "Target B",
            "variant_key": "foxs_cunning",
            "variant_label": "Esperteza da Raposa",
            "manual_notes": [
                {
                    "key": "recall",
                    "label": "Observação",
                    "description": "Sem efeito secundário automatizado.",
                }
            ],
        },
    ]


def _target_variant_assignments() -> list[dict]:
    return [
        {
            "target_participant_id": "e1",
            "target_ref_id": "enemy-1",
            "variant_key": "bears_endurance",
            "variant_label": "Resistência do Urso",
        },
        {
            "target_participant_id": "e2",
            "target_ref_id": "enemy-2",
            "variant_key": "foxs_cunning",
            "variant_label": "Esperteza da Raposa",
        },
    ]


class ModalPendingResolutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        self.state = _build_state()
        self.attacker_state = _attacker_state()

    def _get_stats_side_effect(self, _db, ref_id, kind, _session_id):
        if ref_id == "player-1" and kind == "player":
            return (self.attacker_state, 12, 10, 10, 3, 4)
        raise AssertionError(f"Unexpected stats lookup: {ref_id}/{kind}")

    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    async def test_resolve_pending_save_uses_assignment_for_resolved_target(
        self,
        _mock_emit_entity_hp_update,
        _mock_emit_state,
        mock_emit_log,
    ):
        target_b = self.state.participants[2]
        target_b["pending_save"] = {
            "id": "pending-save-1",
            "status": "pending",
            "spell_name": "Modal Save Test Spell",
            "spell_canonical_key": "modal_save_test_spell",
            "action_kind": "saving_throw",
            "save_ability": "wisdom",
            "save_dc": 15,
            "effect_kind": "damage",
            "effect_bonus": 0,
            "effect_dice": "1d6",
            "effect_roll_required": True,
            "save_success_outcome": "none",
            "damage_type": "psychic",
            "attacker_ref_id": "player-1",
            "attacker_participant_id": "p1",
            "attacker_display_name": "Mage",
            "variant_scope": "per_target",
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
            "target_variant_assignments": _target_variant_assignments(),
            "manual_notes_by_target": _manual_notes(),
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "params": {"ability": "intelligence"},
                    "stacking": "replace",
                }
            ],
            "on_end_effects": [],
        }

        save_roll = RollResult(
            event_id="save-roll-1",
            roll_type="save",
            actor_kind="session_entity",
            actor_ref_id="enemy-2",
            actor_display_name="Target B",
            rolls=[5],
            selected_roll=5,
            advantage_mode="normal",
            modifier_used=0,
            override_used=False,
            formula="1d20 + 0",
            total=5,
            ability="wisdom",
            dc=15,
            success=False,
            timestamp=datetime.now(timezone.utc),
        )

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ), patch(
            "app.services.combat.CombatService._build_roll_actor_stats_for_save",
            return_value=MagicMock(),
        ), patch(
            "app.services.combat.CombatService._create_pending_spell_effect",
            wraps=CombatService._create_pending_spell_effect,
        ), patch(
            "app.services.combat_service.save_resolve.resolve_saving_throw",
            return_value=save_roll,
        ):
            result = await CombatService.resolve_pending_save(
                self.db,
                "session-modal-pending",
                CombatResolveSaveRequest(
                    target_participant_id="e2",
                    pending_save_id="pending-save-1",
                ),
                "user-1",
                True,
            )

        pending_spell = self.state.participants[0]["pending_attack"]
        self.assertEqual(result["selected_variant_key"], "foxs_cunning")
        self.assertEqual(pending_spell["selected_variant_key"], "foxs_cunning")
        self.assertEqual(
            pending_spell["target_variant_assignments"][1]["target_participant_id"], "e2"
        )
        self.assertEqual(
            pending_spell["manual_notes_by_target"][1]["variant_key"], "foxs_cunning"
        )
        self.assertIn("Notas manuais", mock_emit_log.await_args.args[1]["message"])

    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    async def test_cast_spell_effect_applies_only_target_variant_effect(
        self,
        _mock_emit_entity_hp_update,
        _mock_emit_state,
        mock_emit_log,
    ):
        attacker = self.state.participants[0]
        target_b = self.state.participants[2]
        attacker["pending_attack"] = {
            "id": "pending-spell-1",
            "type": "player_spell_effect",
            "spell_name": "Modal Save Test Spell",
            "spell_canonical_key": "modal_save_test_spell",
            "action_kind": "saving_throw",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "damage_type": "psychic",
            "target_ref_id": "enemy-2",
            "target_kind": "session_entity",
            "target_display_name": "Target B",
            "variant_scope": "per_target",
            "selected_variant_key": "bears_endurance",
            "selected_variant_label": "Resistência do Urso",
            "target_variant_assignments": _target_variant_assignments(),
            "manual_notes_by_target": _manual_notes(),
            "effects": [
                {
                    "type": "advantage_on_checks",
                    "target": "selected_target",
                    "params": {"ability": "intelligence"},
                    "stacking": "replace",
                }
            ],
            "on_end_effects": [],
        }

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ):
            result = await CombatService.cast_spell_effect(
                self.db,
                "session-modal-pending",
                CombatResolveSpellEffectRequest(
                    actor_participant_id="p1",
                    pending_spell_id="pending-spell-1",
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["selected_variant_key"], "foxs_cunning")
        self.assertEqual(len(target_b["active_effects"]), 1)
        self.assertEqual(
            target_b["active_effects"][0]["metadata"]["declarative_effect"]["params"]["ability"],
            "intelligence",
        )
        self.assertEqual(len(result["manual_notes_by_target"]), 2)
        self.assertEqual(
            result["manual_notes_by_target"][1]["target_participant_id"],
            "e2",
        )
        self.assertEqual(
            result["manual_notes_by_target"][1]["variant_key"],
            "foxs_cunning",
        )
        self.assertEqual(
            result["manual_notes_by_target"][1]["manual_notes"][0]["label"],
            "Observação",
        )
        self.assertEqual(
            result["manual_notes_by_target"][0]["variant_key"],
            "bears_endurance",
        )
        self.assertEqual(
            result["applied_declarative_effects_by_target"],
            [
                {
                    "target_display_name": "Target B",
                    "target_participant_id": "e2",
                    "target_ref_id": "enemy-2",
                    "variant_key": "foxs_cunning",
                    "variant_label": "Esperteza da Raposa",
                    "effects": [
                        {
                            "type": "advantage_on_checks",
                            "params": {"ability": "intelligence"},
                        }
                    ],
                }
            ],
        )
        final_log = mock_emit_log.await_args.args[1]["message"]
        self.assertIn("Target B: Observação", final_log)
        self.assertIn("Target A: PV temporários", final_log)

    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_entity_hp_update", new_callable=AsyncMock)
    async def test_pending_spell_result_keeps_resolved_target_variant_and_notes(
        self,
        _mock_emit_entity_hp_update,
        _mock_emit_state,
        mock_emit_log,
    ):
        attacker = self.state.participants[0]
        attacker["pending_attack"] = {
            "id": "pending-spell-3",
            "type": "player_spell_effect",
            "spell_name": "Modal Save Test Spell",
            "spell_canonical_key": "modal_save_test_spell",
            "action_kind": "saving_throw",
            "effect_kind": "damage",
            "effect_dice": "1d6",
            "effect_bonus": 0,
            "damage_type": "psychic",
            "target_ref_id": "enemy-1",
            "target_kind": "session_entity",
            "target_display_name": "Target A",
            "is_saved": False,
            "save_success_outcome": "none",
            "variant_scope": "per_target",
            "selected_variant_key": "foxs_cunning",
            "selected_variant_label": "Esperteza da Raposa",
            "target_variant_assignments": _target_variant_assignments(),
            "manual_notes_by_target": _manual_notes(),
            "effects": [],
            "on_end_effects": [],
        }

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ), patch(
            "app.services.combat.CombatService._apply_damage_to_target",
            return_value=(4, "", 10, None),
        ):
            result = await CombatService.cast_spell_effect(
                self.db,
                "session-modal-pending",
                CombatResolveSpellEffectRequest(
                    actor_participant_id="p1",
                    pending_spell_id="pending-spell-3",
                    roll_source="manual",
                    manual_rolls=[4],
                ),
                "user-1",
                False,
            )

        self.assertEqual(result["selected_variant_key"], "bears_endurance")
        self.assertEqual(result["target_display_name"], "Target A")
        self.assertEqual(result["manual_notes_by_target"][0]["target_participant_id"], "e1")
        self.assertEqual(result["manual_notes_by_target"][0]["variant_key"], "bears_endurance")
        self.assertEqual(result["manual_notes_by_target"][0]["manual_notes"][0]["label"], "PV temporários")
        self.assertEqual(result["manual_notes_by_target"][1]["variant_key"], "foxs_cunning")
        final_log = mock_emit_log.await_args.args[1]["message"]
        self.assertIn("Target A: PV temporários", final_log)
        self.assertIn("Target B: Observação", final_log)

    async def test_cast_spell_effect_fails_when_target_assignment_is_missing(self):
        attacker = self.state.participants[0]
        attacker["pending_attack"] = {
            "id": "pending-spell-2",
            "type": "player_spell_effect",
            "spell_name": "Modal Save Test Spell",
            "spell_canonical_key": "modal_save_test_spell",
            "action_kind": "saving_throw",
            "effect_kind": "damage",
            "effect_dice": None,
            "effect_bonus": 0,
            "damage_type": "psychic",
            "target_ref_id": "enemy-2",
            "target_kind": "session_entity",
            "target_display_name": "Target B",
            "variant_scope": "per_target",
            "selected_variant_key": "bears_endurance",
            "target_variant_assignments": [_target_variant_assignments()[0]],
            "manual_notes_by_target": _manual_notes(),
            "effects": [],
            "on_end_effects": [],
        }

        with patch("app.services.combat.CombatService.get_state", return_value=self.state), patch(
            "app.services.combat.CombatService._get_stats",
            side_effect=self._get_stats_side_effect,
        ):
            with self.assertRaises(CombatServiceError):
                await CombatService.cast_spell_effect(
                    self.db,
                    "session-modal-pending",
                    CombatResolveSpellEffectRequest(
                        actor_participant_id="p1",
                        pending_spell_id="pending-spell-2",
                    ),
                    "user-1",
                    False,
                )
