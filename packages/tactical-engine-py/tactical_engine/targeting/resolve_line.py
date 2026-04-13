from shared_contracts import Coordinate, Obstacle
from ..validation.obstacle_rules import blocks_targeting


def resolve_line(
    origin: Coordinate,
    anchor: Coordinate,
    range_: int,
    obstacles: list[Obstacle],
) -> list[Coordinate]:
    result: list[Coordinate] = []
    delta_x = _sign(anchor.x - origin.x)
    delta_y = _sign(anchor.y - origin.y)

    for step in range(1, range_ + 1):
        coordinate = Coordinate(x=origin.x + delta_x * step, y=origin.y + delta_y * step)
        if blocks_targeting(obstacles, coordinate):
            break
        result.append(coordinate)

    return result


def _sign(v: int) -> int:
    if v > 0:
        return 1
    if v < 0:
        return -1
    return 0
