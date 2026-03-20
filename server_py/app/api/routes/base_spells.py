from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.base_spell import BaseSpell, BaseSpellAlias, SpellSchool
from app.models.campaign import RoleMode, SystemType
from app.models.user import User
from app.schemas.base_spell import BaseSpellAliasRead, BaseSpellRead, BaseSpellUpdate
from app.services.base_spells import (
    delete_base_spell as delete_base_spell_svc,
    get_base_spell_by_id,
    list_base_spell_aliases,
    list_base_spells as list_catalog_base_spells,
    update_base_spell as update_base_spell_svc,
)

router = APIRouter()


def require_spell_catalog_editor(user: User) -> None:
    if user.role != RoleMode.GM:
        raise HTTPException(status_code=403, detail="GM required")


def to_base_spell_alias_read(alias: BaseSpellAlias) -> BaseSpellAliasRead:
    return BaseSpellAliasRead(
        id=alias.id,
        alias=alias.alias,
        locale=alias.locale,
        aliasType=alias.alias_type,
    )


def to_base_spell_read(
    spell: BaseSpell,
    aliases: list[BaseSpellAlias],
) -> BaseSpellRead:
    return BaseSpellRead(
        id=spell.id,
        system=spell.system,
        canonicalKey=spell.canonical_key,
        nameEn=spell.name_en,
        namePt=spell.name_pt,
        descriptionEn=spell.description_en,
        descriptionPt=spell.description_pt,
        level=spell.level,
        school=spell.school,
        classesJson=spell.classes_json,
        castingTime=spell.casting_time,
        rangeText=spell.range_text,
        duration=spell.duration,
        componentsJson=spell.components_json,
        materialComponentText=spell.material_component_text,
        concentration=spell.concentration,
        ritual=spell.ritual,
        damageType=spell.damage_type,
        savingThrow=spell.saving_throw,
        source=spell.source,
        sourceRef=spell.source_ref,
        isSrd=spell.is_srd,
        isActive=spell.is_active,
        aliases=[to_base_spell_alias_read(a) for a in aliases],
    )


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
    aliases_by_spell_id = list_base_spell_aliases(
        db=session,
        base_spell_ids=[s.id for s in spells if s.id],
    )
    return [
        to_base_spell_read(spell, aliases_by_spell_id.get(spell.id, []))
        for spell in spells
    ]


@router.get("/{base_spell_id}", response_model=BaseSpellRead)
def get_base_spell(
    base_spell_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    spell = get_base_spell_by_id(db=session, base_spell_id=base_spell_id)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")

    aliases_by_spell_id = list_base_spell_aliases(
        db=session,
        base_spell_ids=[base_spell_id],
    )
    return to_base_spell_read(spell, aliases_by_spell_id.get(base_spell_id, []))


@router.put("/{base_spell_id}", response_model=BaseSpellRead)
def update_base_spell(
    base_spell_id: str,
    payload: BaseSpellUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_spell_catalog_editor(user)
    # Map camelCase payload fields to snake_case model fields
    field_map = {
        "nameEn": "name_en",
        "namePt": "name_pt",
        "descriptionEn": "description_en",
        "descriptionPt": "description_pt",
        "classesJson": "classes_json",
        "castingTime": "casting_time",
        "rangeText": "range_text",
        "componentsJson": "components_json",
        "materialComponentText": "material_component_text",
        "damageType": "damage_type",
        "savingThrow": "saving_throw",
    }
    data = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        db_key = field_map.get(key, key)
        data[db_key] = value

    spell = update_base_spell_svc(db=session, base_spell_id=base_spell_id, data=data)
    if not spell:
        raise HTTPException(status_code=404, detail="Base spell not found")

    aliases_by_spell_id = list_base_spell_aliases(
        db=session,
        base_spell_ids=[base_spell_id],
    )
    return to_base_spell_read(spell, aliases_by_spell_id.get(base_spell_id, []))


@router.delete("/{base_spell_id}", status_code=204)
def delete_base_spell(
    base_spell_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_spell_catalog_editor(user)
    deleted = delete_base_spell_svc(db=session, base_spell_id=base_spell_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Base spell not found")
