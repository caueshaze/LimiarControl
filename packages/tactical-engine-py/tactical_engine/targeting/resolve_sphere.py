from shared_contracts import Coordinate, Obstacle
from ..grid.coordinates import chebyshev_distance
from ..validation.obstacle_rules import blocks_targeting


def resolve_sphere(
    center: Coordinate,
    radius: int,
    obstacles: list[Obstacle],
) -> list[Coordinate]:
    result: list[Coordinate] = []
    for x in range(center.x - radius, center.x + radius + 1):
        for y in range(center.y - radius, center.y + radius + 1):
            coordinate = Coordinate(x=x, y=y)
            if chebyshev_distance(center, coordinate) <= radius and not blocks_targeting(obstacles, coordinate):
                result.append(coordinate)
    return result
