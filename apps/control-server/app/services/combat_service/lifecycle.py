from __future__ import annotations

from app.schemas.combat import CombatMapSelection

from .lifecycle_initiative import CombatLifecycleInitiativeMixin
from .lifecycle_turns import CombatLifecycleTurnsMixin


class CombatLifecycleMixin(CombatLifecycleInitiativeMixin, CombatLifecycleTurnsMixin):
    _INITIATIVE_SKIPPED_STATUSES = {"dead", "defeated", "stable"}
    _DEMO_MAP_SELECTION = CombatMapSelection(
        kind="demo_map",
        mapId=None,
        mapName="Demo Encounter",
        imageUrl="/maps/map.jpg",
        gridWidth=20,
        gridHeight=14,
        calibration={"x": 0, "y": 0, "width": 1, "height": 1},
    )
