from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.class_progression import get_class_spell_progression

router = APIRouter()


class ClassSpellProgressionResponse(BaseModel):
    className: str
    level: int
    slots: dict[int, int]
    maxSpellLevel: int
    cantrips: int
    leveledSpellsKnown: int | None
    spellcastingType: str | None


@router.get("/spell-progression", response_model=ClassSpellProgressionResponse)
def get_spell_progression(
    class_name: str = Query(..., alias="class"),
    level: int = Query(..., ge=1, le=20),
    _user: User = Depends(get_current_user),
) -> ClassSpellProgressionResponse:
    """Return pure class spell progression for a given class and character level.

    Does not include prepared spell counts — those depend on character ability scores
    and are computed on the frontend from this data.
    """
    result = get_class_spell_progression(class_name, level)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No spell progression found for class '{class_name}'",
        )
    return ClassSpellProgressionResponse(**result)
