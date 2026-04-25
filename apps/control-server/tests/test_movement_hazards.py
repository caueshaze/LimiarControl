from __future__ import annotations

import unittest
from unittest.mock import patch

from app.services.combat_service.movement_hazards import (
    compute_movement_hazard_outcomes,
)


def _spike_growth_effect(
    *,
    affected_cells: list[dict[str, int]],
    effect_id: str = "effect-spike-1",
) -> dict:
    return {
        "id": effect_id,
        "source_spell_canonical_key": "spike_growth",
        "source_spell_name": "Spike Growth",
        "effect_kind": "hazard",
        "terrain_effect": "difficult_terrain",
        "movement_damage_dice": "2d4",
        "damage_type": "Piercing",
        "damage_per_meters": 1.5,
        "affected_cells": affected_cells,
    }


def _fog_cloud_effect(affected_cells: list[dict[str, int]]) -> dict:
    return {
        "id": "effect-fog",
        "source_spell_canonical_key": "fog_cloud",
        "source_spell_name": "Fog Cloud",
        "effect_kind": "obscurement",
        "obscurement": "heavily_obscured",
        "affected_cells": affected_cells,
    }


def _bare_difficult_terrain(affected_cells: list[dict[str, int]]) -> dict:
    return {
        "id": "effect-rough",
        "source_spell_name": "Rough ground",
        "terrain_effect": "difficult_terrain",
        "affected_cells": affected_cells,
    }


class TestMovementHazardOutcomes(unittest.TestCase):
    def test_path_outside_effect_yields_no_outcome(self):
        effect = _spike_growth_effect(affected_cells=[{"x": 5, "y": 5}, {"x": 5, "y": 6}])
        path = [{"x": 1, "y": 1}, {"x": 2, "y": 1}, {"x": 3, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect], path)

        self.assertEqual(outcomes, [])

    @patch(
        "app.services.combat_service.movement_hazards._roll_dice_expression",
        return_value=5,
    )
    def test_path_partially_through_effect_rolls_per_cell(self, mock_roll):
        effect = _spike_growth_effect(
            affected_cells=[{"x": 3, "y": 1}, {"x": 4, "y": 1}],
        )
        # Path enters 2 affected cells -> 3.0 meters -> floor(3.0/1.5)=2 instances
        path = [{"x": 2, "y": 1}, {"x": 3, "y": 1}, {"x": 4, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect], path)

        self.assertEqual(len(outcomes), 1)
        outcome = outcomes[0]
        self.assertEqual(outcome["cells_inside"], 2)
        self.assertEqual(outcome["damage_instances"], 2)
        self.assertEqual(outcome["damage"], 10)
        self.assertEqual(outcome["dice_expression"], "2d4")
        self.assertEqual(outcome["damage_type"], "Piercing")
        self.assertEqual(mock_roll.call_count, 2)

    @patch(
        "app.services.combat_service.movement_hazards._roll_dice_expression",
        return_value=4,
    )
    def test_path_fully_inside_effect(self, mock_roll):
        effect = _spike_growth_effect(
            affected_cells=[
                {"x": 1, "y": 1},
                {"x": 2, "y": 1},
                {"x": 3, "y": 1},
                {"x": 4, "y": 1},
            ],
        )
        path = [{"x": 2, "y": 1}, {"x": 3, "y": 1}, {"x": 4, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect], path)

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["cells_inside"], 3)
        self.assertEqual(outcomes[0]["damage_instances"], 3)
        self.assertEqual(outcomes[0]["damage"], 12)
        self.assertEqual(mock_roll.call_count, 3)

    def test_empty_path_yields_no_outcome(self):
        effect = _spike_growth_effect(affected_cells=[{"x": 1, "y": 1}])
        self.assertEqual(compute_movement_hazard_outcomes([effect], []), [])
        self.assertEqual(compute_movement_hazard_outcomes([effect], None), [])

    def test_no_active_effects_yields_no_outcome(self):
        path = [{"x": 1, "y": 1}, {"x": 2, "y": 1}]
        self.assertEqual(compute_movement_hazard_outcomes([], path), [])
        self.assertEqual(compute_movement_hazard_outcomes(None, path), [])

    def test_fog_cloud_is_no_op(self):
        effect = _fog_cloud_effect(
            affected_cells=[{"x": 2, "y": 1}, {"x": 3, "y": 1}],
        )
        path = [{"x": 2, "y": 1}, {"x": 3, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect], path)

        self.assertEqual(outcomes, [])

    def test_bare_difficult_terrain_without_damage_dice_is_no_op(self):
        effect = _bare_difficult_terrain(
            affected_cells=[{"x": 2, "y": 1}, {"x": 3, "y": 1}],
        )
        path = [{"x": 2, "y": 1}, {"x": 3, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect], path)

        self.assertEqual(outcomes, [])

    @patch(
        "app.services.combat_service.movement_hazards._roll_dice_expression",
        return_value=3,
    )
    def test_overlapping_distinct_effects_each_roll_independently(self, mock_roll):
        effect_a = _spike_growth_effect(
            affected_cells=[{"x": 2, "y": 1}, {"x": 3, "y": 1}],
            effect_id="effect-a",
        )
        effect_b = _spike_growth_effect(
            affected_cells=[{"x": 3, "y": 1}, {"x": 4, "y": 1}],
            effect_id="effect-b",
        )
        path = [{"x": 2, "y": 1}, {"x": 3, "y": 1}, {"x": 4, "y": 1}]

        outcomes = compute_movement_hazard_outcomes([effect_a, effect_b], path)

        self.assertEqual(len(outcomes), 2)
        ids = sorted(o["effect_id"] for o in outcomes)
        self.assertEqual(ids, ["effect-a", "effect-b"])
        # 4 total roll calls (2 instances per effect)
        self.assertEqual(mock_roll.call_count, 4)

    def test_short_path_below_per_meters_threshold_yields_no_outcome(self):
        effect = _spike_growth_effect(affected_cells=[{"x": 2, "y": 1}])
        # 1 cell = 1.5m -> exactly 1 instance, not zero
        with patch(
            "app.services.combat_service.movement_hazards._roll_dice_expression",
            return_value=2,
        ):
            outcomes = compute_movement_hazard_outcomes(
                [effect], [{"x": 2, "y": 1}]
            )
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["damage_instances"], 1)


if __name__ == "__main__":
    unittest.main()
