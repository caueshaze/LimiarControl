def is_stale_version(known_version: int, current_version: int) -> bool:
    return known_version < current_version


def next_encounter_version(current_version: int) -> int:
    return current_version + 1
