"""Paridade com packages/tactical-engine/tests/unit/targeting-shapes.test.ts"""
from shared_contracts import Coordinate, Obstacle
from tactical_engine import resolve_cone, resolve_cube, resolve_cylinder, resolve_line, resolve_sphere


def _obstacle(id_: str, cells: list[Coordinate], *, blocks_spell: bool = False, blocks_targeting: bool = False) -> Obstacle:
    return Obstacle(
        id=id_,
        battle_map_id="map",
        cells=cells,
        blocks_movement=False,
        blocks_targeting=blocks_targeting,
        blocks_spell=blocks_spell,
        blocks_vision=False,
        cover="none",
        clips_diagonal_movement=False,
    )


def test_resolves_line_without_blocked_cells():
    result = resolve_line(Coordinate(x=0, y=0), Coordinate(x=3, y=0), 3, [])
    assert result == [Coordinate(x=1, y=0), Coordinate(x=2, y=0), Coordinate(x=3, y=0)]


def test_resolves_area_shapes_deterministically():
    assert len(resolve_cone(Coordinate(x=1, y=1), Coordinate(x=3, y=1), 2, [])) > 0
    assert len(resolve_sphere(Coordinate(x=2, y=2), 1, [])) > 0
    assert resolve_cylinder(Coordinate(x=2, y=2), 1, []) == resolve_sphere(Coordinate(x=2, y=2), 1, [])
    assert len(resolve_cube(Coordinate(x=2, y=2), 2, [])) == 4


def test_spells_pass_through_movement_only_obstacles_but_block_on_spell_blockers():
    obstacles = [
        Obstacle(
            id="move-only",
            battle_map_id="map",
            cells=[Coordinate(x=1, y=0)],
            blocks_movement=True,
            blocks_targeting=False,
            blocks_spell=False,
            blocks_vision=False,
            cover="none",
            clips_diagonal_movement=True,
        ),
        Obstacle(
            id="spell-block",
            battle_map_id="map",
            cells=[Coordinate(x=2, y=0)],
            blocks_movement=False,
            blocks_targeting=False,
            blocks_spell=True,
            blocks_vision=False,
            cover="none",
            clips_diagonal_movement=False,
        ),
    ]
    result = resolve_line(Coordinate(x=0, y=0), Coordinate(x=3, y=0), 3, obstacles)
    assert result == [Coordinate(x=1, y=0)]
