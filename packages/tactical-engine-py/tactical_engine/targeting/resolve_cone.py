from shared_contracts import Coordinate, Obstacle
from ..validation.obstacle_rules import blocks_targeting


def resolve_cone(
    origin: Coordinate,
    anchor: Coordinate,
    size: int,
    obstacles: list[Obstacle],
) -> list[Coordinate]:
    result: list[Coordinate] = []
    delta_x = _sign(anchor.x - origin.x)
    delta_y = _sign(anchor.y - origin.y)

    for step in range(1, size + 1):
        for spread in range(-step + 1, step):
            if abs(delta_x) >= abs(delta_y):
                coordinate = Coordinate(x=origin.x + delta_x * step, y=origin.y + spread)
            else:
                coordinate = Coordinate(x=origin.x + spread, y=origin.y + delta_y * step)
            if not blocks_targeting(obstacles, coordinate):
                result.append(coordinate)

    return result


def _sign(v: int) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0
