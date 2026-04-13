from shared_contracts import Coordinate, Obstacle
from ..validation.obstacle_rules import blocks_targeting


def resolve_cube(
    anchor: Coordinate,
    size: int,
    obstacles: list[Obstacle],
) -> list[Coordinate]:
    result: list[Coordinate] = []
    for x in range(anchor.x, anchor.x + size):
        for y in range(anchor.y, anchor.y + size):
            coordinate = Coordinate(x=x, y=y)
            if not blocks_targeting(obstacles, coordinate):
                result.append(coordinate)
    return result
