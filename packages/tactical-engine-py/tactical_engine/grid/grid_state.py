from dataclasses import dataclass
from typing import Optional
from shared_contracts import BattleMap, Coordinate, Obstacle, Token
from .coordinates import coordinate_key


@dataclass
class GridState:
    map: BattleMap
    obstacles: list[Obstacle]
    tokens: list[Token]


def is_inside_map(grid_state: GridState, coordinate: Coordinate) -> bool:
    return (
        coordinate.x >= 0
        and coordinate.y >= 0
        and coordinate.x < grid_state.map.grid_width
        and coordinate.y < grid_state.map.grid_height
    )


def is_blocked_cell(grid_state: GridState, coordinate: Coordinate) -> bool:
    key = coordinate_key(coordinate)
    return any(
        obstacle.blocks_movement and any(coordinate_key(cell) == key for cell in obstacle.cells)
        for obstacle in grid_state.obstacles
    )


def find_occupying_token(grid_state: GridState, coordinate: Coordinate) -> Optional[Token]:
    key = coordinate_key(coordinate)
    return next(
        (token for token in grid_state.tokens if coordinate_key(token.position) == key),
        None,
    )
