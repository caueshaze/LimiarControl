from shared_contracts import Coordinate, Obstacle, ObstacleCover
from ..grid.coordinates import coordinate_key

_COVER_RANK: dict[ObstacleCover, int] = {
    "none": 0,
    "half": 1,
    "threeQuarters": 2,
    "full": 3,
}


def _has_obstacle_at_cell(
    obstacles: list[Obstacle],
    coordinate: Coordinate,
    predicate,
) -> bool:
    key = coordinate_key(coordinate)
    return any(
        predicate(obstacle) and any(coordinate_key(cell) == key for cell in obstacle.cells)
        for obstacle in obstacles
    )


def blocks_spell_effects(obstacles: list[Obstacle], coordinate: Coordinate) -> bool:
    return _has_obstacle_at_cell(
        obstacles,
        coordinate,
        lambda o: o.blocks_spell or o.blocks_targeting,
    )


def blocks_targeting(obstacles: list[Obstacle], coordinate: Coordinate) -> bool:
    return blocks_spell_effects(obstacles, coordinate)


def blocks_vision(obstacles: list[Obstacle], coordinate: Coordinate) -> bool:
    return _has_obstacle_at_cell(obstacles, coordinate, lambda o: o.blocks_vision)


def clips_diagonal_movement(obstacles: list[Obstacle], coordinate: Coordinate) -> bool:
    return _has_obstacle_at_cell(obstacles, coordinate, lambda o: o.clips_diagonal_movement)


def get_highest_cover(obstacles: list[Obstacle], coordinate: Coordinate) -> ObstacleCover:
    highest: ObstacleCover = "none"
    key = coordinate_key(coordinate)
    for obstacle in obstacles:
        if not any(coordinate_key(cell) == key for cell in obstacle.cells):
            continue
        if _COVER_RANK[obstacle.cover] > _COVER_RANK[highest]:
            highest = obstacle.cover
    return highest
