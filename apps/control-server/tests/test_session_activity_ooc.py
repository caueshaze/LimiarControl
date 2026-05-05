import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.api.routes.sessions.activity import get_session_activity


def _make_user(user_id: str = "user-1"):
    user = MagicMock()
    user.id = user_id
    return user


class TestSessionActivityOutOfCombatEvents(unittest.TestCase):
    def test_maps_out_of_combat_activity_events(self):
        entry = MagicMock()
        entry.id = "session-1"
        entry.campaign_id = "camp-1"
        entry.started_at = None
        entry.created_at = None

        member = MagicMock()
        member.id = "member-1"

        cast_cmd = MagicMock()
        cast_cmd.user_id = "caster-1"
        cast_cmd.actor_name = "Caster One"
        cast_cmd.command_type = "out_of_combat_spell_cast"
        cast_cmd.created_at = datetime(2026, 5, 5, 10, 0, 0, tzinfo=timezone.utc)
        cast_cmd.payload_json = {
            "actor_user_id": "gm-1",
            "actor_player_user_id": "caster-1",
            "actor_display_name": "Caster One",
            "caster_player_user_id": "ally-a",
            "caster_display_name": "Aelar",
            "target_player_user_id": "ally-b",
            "target_display_name": "Ally B",
            "spell_key": "enhance_ability",
            "spell_name": "Melhorar Habilidade",
            "variant_key": "owls_wisdom",
            "variant_label": "Sabedoria da Coruja",
            "slot_level": 2,
            "created_effect_ids": ["eff-1", "eff-2"],
            "concentration_group": "grp-2",
            "replaced_concentration": True,
            "previous_concentration_group": "grp-1",
            "new_concentration_group": "grp-2",
            "previous_spell_name": "Benção",
            "previous_variant_label": None,
            "cast_by_gm": True,
        }

        remove_cmd = MagicMock()
        remove_cmd.user_id = "caster-1"
        remove_cmd.actor_name = "Caster One"
        remove_cmd.command_type = "out_of_combat_effect_removed"
        remove_cmd.created_at = datetime(2026, 5, 5, 10, 1, 0, tzinfo=timezone.utc)
        remove_cmd.payload_json = {
            "actor_player_user_id": "caster-1",
            "actor_display_name": "Caster One",
            "removed_effect_id": "eff-2",
            "effect_label": "Escudo da Fé",
            "source_spell_name": "Escudo da Fé",
            "variant_label": None,
            "concentration_group": "grp-2",
            "broke_concentration_group": True,
        }

        db = MagicMock()
        call_count = [0]

        def exec_side(query):
            result = MagicMock()
            idx = call_count[0]
            call_count[0] += 1
            if idx == 0:
                result.first.return_value = entry
            elif idx == 1:
                result.first.return_value = member
            elif idx in (2, 3):
                result.all.return_value = []
            else:
                result.all.return_value = [
                    (cast_cmd, MagicMock(username="caster", display_name="Caster One")),
                    (remove_cmd, MagicMock(username="caster", display_name="Caster One")),
                ]
            return result

        db.exec.side_effect = exec_side

        events = get_session_activity("session-1", user=_make_user(), session=db)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].type, "out_of_combat_spell_cast")
        self.assertEqual(events[0].spellName, "Melhorar Habilidade")
        self.assertEqual(events[0].actorUserId, "gm-1")
        self.assertEqual(events[0].casterDisplayName, "Aelar")
        self.assertEqual(events[0].targetDisplayName, "Ally B")
        self.assertTrue(events[0].castByGm)
        self.assertEqual(events[0].slotLevel, 2)
        self.assertEqual(events[1].type, "out_of_combat_effect_removed")
        self.assertEqual(events[1].effectLabel, "Escudo da Fé")
        self.assertTrue(events[1].brokeConcentrationGroup)
