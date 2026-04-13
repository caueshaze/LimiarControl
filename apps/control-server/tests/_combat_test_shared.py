import unittest
from unittest.mock import MagicMock, patch

from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatPhase, CombatState
from app.models.item import Item, ItemType
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity import CombatAction
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatEntityActionRequest,
    CombatParticipant,
    CombatSetInitiativeParticipant,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.services.combat import (
    CombatService,
    CombatServiceError,
    _parse_dice,
    _roll_dice_expression,
)


class TestResolutionTypeMapping(unittest.TestCase):
    def test_maps_spell_attack(self):
        self.assertEqual(CombatService._map_resolution_type_to_spell_mode("spell_attack"), "spell_attack")

    def test_maps_saving_throw(self):
        self.assertEqual(CombatService._map_resolution_type_to_spell_mode("saving_throw"), "saving_throw")

    def test_maps_heal(self):
        self.assertEqual(CombatService._map_resolution_type_to_spell_mode("heal"), "heal")

    def test_maps_automatic_to_direct_damage(self):
        self.assertEqual(CombatService._map_resolution_type_to_spell_mode("automatic"), "direct_damage")

    def test_none_resolution_returns_none(self):
        self.assertIsNone(CombatService._map_resolution_type_to_spell_mode("none"))

    def test_null_returns_none(self):
        self.assertIsNone(CombatService._map_resolution_type_to_spell_mode(None))

    def test_unknown_string_returns_none(self):
        self.assertIsNone(CombatService._map_resolution_type_to_spell_mode("unknown"))

    def test_non_string_returns_none(self):
        self.assertIsNone(CombatService._map_resolution_type_to_spell_mode(42))


class TestCombatDiceParser(unittest.TestCase):
    def test_parse_dice(self):
        self.assertEqual(_parse_dice("1d8"), (1, 8, 0))
        self.assertEqual(_parse_dice("2d6+3"), (2, 6, 3))
        self.assertEqual(_parse_dice("1d10 - 1"), (1, 10, -1))
        self.assertEqual(_parse_dice(""), (0, 0, 0))
        self.assertEqual(_parse_dice("invalid"), (0, 0, 0))

    @patch("random.randint", return_value=5)
    def test_roll_dice_expression(self, mock_randint):
        self.assertEqual(_roll_dice_expression("1d8"), 5)
        self.assertEqual(_roll_dice_expression("2d6+3"), 13) # 5 + 5 + 3
        self.assertEqual(_roll_dice_expression("1d10 - 1"), 4)
        
        # Critical test
        self.assertEqual(_roll_dice_expression("1d8", critical=True), 10) # 5 + 5

class TestCombatServiceBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = MagicMock()
        
        self.state = CombatState(
            id="combat-123",
            session_id="session-123",
            phase=CombatPhase.initiative,
            round=1,
            current_turn_index=0,
            participants=[
                {
                    "id": "p1",
                    "ref_id": "player-123",
                    "kind": "player",
                    "display_name": "Hero",
                    "initiative": None,
                    "status": "active",
                    "team": "players",
                    "visible": True,
                    "actor_user_id": "user-1"
                },
                {
                    "id": "e1",
                    "ref_id": "enemy-123",
                    "kind": "session_entity",
                    "display_name": "Goblin",
                    "initiative": None,
                    "status": "active",
                    "team": "enemies",
                    "visible": True,
                    "actor_user_id": None
                }
            ]
        )
