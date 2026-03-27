import unittest

from _combat_test_action_economy import CombatActionEconomyTestsMixin
from _combat_test_effects import CombatEffectsTestsMixin
from _combat_test_entity_stats import CombatEntityStatsTestsMixin
from _combat_test_flow import CombatFlowTestsMixin
from _combat_test_npc_turns import CombatNpcTurnTestsMixin
from _combat_test_shared import TestCombatDiceParser, TestCombatServiceBase
from _combat_test_standard_actions import CombatStandardActionTestsMixin
from _combat_test_status import CombatStatusTestsMixin
from _combat_test_structured_actions import CombatStructuredActionTestsMixin


class TestCombatService(
    TestCombatServiceBase,
    CombatFlowTestsMixin,
    CombatEntityStatsTestsMixin,
    CombatStatusTestsMixin,
    CombatNpcTurnTestsMixin,
    CombatStructuredActionTestsMixin,
    CombatEffectsTestsMixin,
    CombatActionEconomyTestsMixin,
    CombatStandardActionTestsMixin,
):
    pass


if __name__ == "__main__":
    unittest.main()
