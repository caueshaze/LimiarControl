from shared_contracts import Coordinate


def coordinate_key(c: Coordinate) -> str:
    return f"{c.x},{c.y}"


def is_same_coordinate(a: Coordinate, b: Coordinate) -> bool:
    return a.x == b.x and a.y == b.y


def chebyshev_distance(a: Coordinate, b: Coordinate) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def manhattan_distance(a: Coordinate, b: Coordinate) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)
