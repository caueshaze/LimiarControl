from shared_contracts import Coordinate


def is_diagonal_step(from_: Coordinate, to: Coordinate) -> bool:
    return abs(from_.x - to.x) == 1 and abs(from_.y - to.y) == 1


def step_cost(from_: Coordinate, to: Coordinate, diagonal_index: int) -> int:
    if not is_diagonal_step(from_, to):
        return 5
    # D&D 5e alternating diagonal rule: 1st diagonal = 5ft, 2nd = 10ft, repeating
    return 5 if diagonal_index % 2 == 0 else 10


def compute_path_cost(path: list[Coordinate]) -> int:
    total = 0
    diagonal_index = 0
    for i in range(1, len(path)):
        cost = step_cost(path[i - 1], path[i], diagonal_index)
        total += cost
        if is_diagonal_step(path[i - 1], path[i]):
            diagonal_index += 1
    return total
