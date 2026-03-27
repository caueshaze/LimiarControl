from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import require_system_admin
from app.api.serializers.base_spell import to_base_spell_read
from app.db.session import get_session
from app.models.base_spell import SpellSchool
from app.models.campaign import SystemType
from app.models.user import User
from app.schemas.base_spell import BaseSpellCreate, BaseSpellRead, BaseSpellUpdate
from app.services.base_spells import (
    create_base_spell,
    delete_base_spell,
    get_base_spell_by_id,
    list_base_spells,
    update_base_spell,
)

router = APIRouter()


@router.get("/base-spells", response_model=list[BaseSpellRead])
def admin_list_base_spells(
    system: SystemType | None = None,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = Query(None, alias="class_name"),
    canonical_key: str | None = None,
    search: str | None = None,
    is_active: bool | None = None,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    spells = list_base_spells(
        db=session,
        system=system,
        level=level,
        school=school,
        class_name=class_name,
        canonical_key=canonical_key,
        search=search,
        is_active=is_active,
    )
    return [to_base_spell_read(spell) for spell in spells]


@router.get("/base-spells/{base_spell_id}", response_model=BaseSpellRead)
def admin_get_base_spell(
    base_spell_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    spell = get_base_spell_by_id(db=session, base_spell_id=base_spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")
    return to_base_spell_read(spell)


@router.post("/base-spells", response_model=BaseSpellRead, status_code=201)
def admin_create_base_spell(
    payload: BaseSpellCreate,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    spell = create_base_spell(db=session, payload=payload)
    return to_base_spell_read(spell)


@router.put("/base-spells/{base_spell_id}", response_model=BaseSpellRead)
def admin_update_base_spell(
    base_spell_id: str,
    payload: BaseSpellUpdate,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    spell = get_base_spell_by_id(db=session, base_spell_id=base_spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")
    updated = update_base_spell(db=session, spell=spell, payload=payload)
    return to_base_spell_read(updated)


@router.delete("/base-spells/{base_spell_id}", status_code=204)
def admin_delete_base_spell(
    base_spell_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    spell = get_base_spell_by_id(db=session, base_spell_id=base_spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")
    delete_base_spell(db=session, spell=spell)
    return None
