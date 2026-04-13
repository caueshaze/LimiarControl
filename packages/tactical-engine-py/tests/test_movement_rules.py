"""Paridade com packages/tactical-engine/tests/unit/movement-rules.test.ts"""
import pytest
from shared_contracts import BattleMap, CombatState, GridCalibration, Obstacle, Token, Coordinate
from tactical_engine import compute_path_cost, validate_movement
from tactical_engine.grid.grid_state import GridState

MAP = BattleMap(
    id="map",
    name="map",
    grid_width=20,
    grid_height=20,
    terrain_version=1,
    grid_calibration=GridCalibration(x=0, y=0, width=1, height=1),
    active_encounter_id="enc",
)

TOKEN = Token(
    id="token",
    battle_map_id="map",
    label="Hero",
    kind="playerCharacter",
    controller_type="player",
    controller_id="player_1",
    position=Coordinate(x=1, y=1),
    movement_speed_base=30,
    movement_budget=30,
    combatant_id="cmb_1",
)

COMBAT_STATE = CombatState(
    id="combat",
    battle_map_id="map",
    status="active",
    round_number=1,
    turn_index=0,
    active_combatant_id="cmb_1",
    initiative_order=["cmb_1"],
    advanced_by="LimiarControl",
    version=1,
)


def test_alternating_diagonal_cost():
    cost = compute_path_cost([
        Coordinate(x=1, y=1),
        Coordinate(x=2, y=2),
        Coordinate(x=3, y=3),
    ])
    assert cost == 15


def test_rejects_blocked_destinations():
    obstacles = [
        Obstacle(
            id="obs",
            battle_map_id="map",
            cells=[Coordinate(x=2, y=2)],
            blocks_movement=True,
            blocks_targeting=True,
            blocks_spell=True,
            blocks_vision=True,
            cover="full",
            clips_diagonal_movement=True,
        )
    ]
    grid = GridState(map=MAP, obstacles=obstacles, tokens=[TOKEN])
    result = validate_movement(grid, TOKEN, [Coordinate(x=2, y=2)], COMBAT_STATE)
    assert result.accepted is False
    assert result.rejection_reason == "blocked_path"


def test_rejects_diagonal_corner_clipping():
    obstacles = [
        Obstacle(
            id="obs-clip",
            battle_map_id="map",
            cells=[Coordinate(x=2, y=1)],
            blocks_movement=True,
            blocks_targeting=False,
            blocks_spell=False,
            blocks_vision=False,
            cover="none",
            clips_diagonal_movement=True,
        )
    ]
    grid = GridState(map=MAP, obstacles=obstacles, tokens=[TOKEN])
    result = validate_movement(grid, TOKEN, [Coordinate(x=2, y=2)], COMBAT_STATE)
    assert result.accepted is False
    assert result.rejection_reason == "diagonal_clipped"


def test_accepts_movement_within_budget():
    path = [
        Coordinate(x=2, y=1),
        Coordinate(x=3, y=1),
        Coordinate(x=4, y=1),
        Coordinate(x=5, y=1),
        Coordinate(x=6, y=1),
        Coordinate(x=7, y=1),
    ]
    grid = GridState(map=MAP, obstacles=[], tokens=[TOKEN])
    result = validate_movement(grid, TOKEN, path, COMBAT_STATE)
    assert result.accepted is True
    assert result.path_cost_units == 30


def test_accepts_movement_exactly_exhausting_budget():
    token = TOKEN.model_copy(update={"movement_budget": 20})
    path = [Coordinate(x=2, y=1), Coordinate(x=3, y=1), Coordinate(x=4, y=1), Coordinate(x=5, y=1)]
    grid = GridState(map=MAP, obstacles=[], tokens=[token])
    result = validate_movement(grid, token, path, COMBAT_STATE)
    assert result.accepted is True
    assert result.path_cost_units == 20


def test_rejects_movement_exceeding_budget():
    token = TOKEN.model_copy(update={"movement_budget": 10})
    path = [Coordinate(x=2, y=1), Coordinate(x=3, y=1), Coordinate(x=4, y=1)]
    grid = GridState(map=MAP, obstacles=[], tokens=[token])
    result = validate_movement(grid, token, path, COMBAT_STATE)
    assert result.accepted is False
    assert result.rejection_reason == "movement_budget_exceeded"


def test_respects_reduced_budget_after_prior_move():
    token = TOKEN.model_copy(update={"movement_budget": 10, "position": Coordinate(x=5, y=1)})
    grid = GridState(map=MAP, obstacles=[], tokens=[token])

    path_ok = [Coordinate(x=6, y=1), Coordinate(x=7, y=1)]
    result_ok = validate_movement(grid, token, path_ok, COMBAT_STATE)
    assert result_ok.accepted is True
    assert result_ok.path_cost_units == 10

    path_too_far = [Coordinate(x=6, y=1), Coordinate(x=7, y=1), Coordinate(x=8, y=1)]
    result_rejected = validate_movement(grid, token, path_too_far, COMBAT_STATE)
    assert result_rejected.accepted is False
    assert result_rejected.rejection_reason == "movement_budget_exceeded"
