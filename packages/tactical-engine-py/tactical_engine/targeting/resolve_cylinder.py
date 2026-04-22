from shared_contracts import Coordinate, Obstacle
from .resolve_sphere import resolve_sphere


def resolve_cylinder(
    center: Coordinate,
    radius: int,
    obstacles: list[Obstacle],
) -> list[Coordinate]:
    """Resolve a cylinder AoE as a 2D circular footprint.

    LimiarMap does not model vertical height in combat targeting. Cylinder
    height is ignored, and the selected point is treated as the center of the
    cylinder's ground projection using the same Chebyshev approximation as
    sphere.
    """
    return resolve_sphere(center, radius, obstacles)
