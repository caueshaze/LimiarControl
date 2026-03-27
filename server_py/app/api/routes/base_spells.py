from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_user
from app.api.serializers.base_spell import to_base_spell_read
from app.db.session import get_session
from app.models.base_spell import SpellSchool
from app.models.campaign import SystemType
from app.models.user import User
from app.schemas.base_spell import BaseSpellRead
from app.services.base_spells import (
    get_base_spell_by_id,
    list_base_spells as list_catalog_base_spells,
)

router = APIRouter()


@router.get("", response_model=list[BaseSpellRead])
def list_base_spells(
    system: SystemType | None = None,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = Query(None, alias="class_name"),
    canonical_key: str | None = None,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    spells = list_catalog_base_spells(
        db=session,
        system=system,
        level=level,
        school=school,
        class_name=class_name,
        canonical_key=canonical_key,
    )
    return [to_base_spell_read(spell) for spell in spells]


@router.get("/{base_spell_id}", response_model=BaseSpellRead)
def get_base_spell(
    base_spell_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    spell = get_base_spell_by_id(db=session, base_spell_id=base_spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")

    return to_base_spell_read(spell)
