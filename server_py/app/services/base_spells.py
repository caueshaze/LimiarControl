from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_spell import BaseSpell, BaseSpellAlias, SpellSchool
from app.models.campaign_spell import CampaignSpell
from app.models.campaign import SystemType
from app.schemas.base_spell import BaseSpellCreate, BaseSpellUpdate


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


# ---------------------------------------------------------------------------
# Field mapping: camelCase schema -> snake_case model
# ---------------------------------------------------------------------------

_FIELD_MAP: dict[str, str] = {
    "nameEn": "name_en",
    "namePt": "name_pt",
    "descriptionEn": "description_en",
    "descriptionPt": "description_pt",
    "classesJson": "classes_json",
    "castingTimeType": "casting_time_type",
    "castingTime": "casting_time",
    "rangeMeters": "range_meters",
    "rangeText": "range_text",
    "targetMode": "target_mode",
    "componentsJson": "components_json",
    "materialComponentText": "material_component_text",
    "resolutionType": "resolution_type",
    "savingThrow": "saving_throw",
    "saveSuccessOutcome": "save_success_outcome",
    "damageDice": "damage_dice",
    "damageType": "damage_type",
    "healDice": "heal_dice",
    "upcast": "upcast_json",
    "upcastMode": "upcast_mode",
    "upcastValue": "upcast_value",
    "sourceRef": "source_ref",
    "isSrd": "is_srd",
    "isActive": "is_active",
    "canonicalKey": "canonical_key",
}


def _to_db_fields(data: dict) -> dict:
    return {_FIELD_MAP.get(k, k): v for k, v in data.items()}


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_base_spells(
    *,
    db: Session,
    system: SystemType | None = None,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = None,
    canonical_key: str | None = None,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[BaseSpell]:
    statement = select(BaseSpell)

    if is_active is not None:
        statement = statement.where(BaseSpell.is_active == is_active)  # noqa: E712
    else:
        statement = statement.where(BaseSpell.is_active == True)  # noqa: E712

    if system is not None:
        statement = statement.where(BaseSpell.system == system)
    if level is not None:
        statement = statement.where(BaseSpell.level == level)
    if school is not None:
        statement = statement.where(BaseSpell.school == school)
    if canonical_key:
        statement = statement.where(
            func.lower(BaseSpell.canonical_key) == _normalize_lookup(canonical_key)
        )
    if search:
        needle = f"%{search.strip().lower()}%"
        statement = statement.where(
            func.lower(BaseSpell.canonical_key).contains(needle)
            | func.lower(BaseSpell.name_en).contains(needle)
            | func.lower(func.coalesce(BaseSpell.name_pt, "")).contains(needle)
        )

    statement = statement.order_by(BaseSpell.level, BaseSpell.name_en)
    results = list(db.exec(statement).all())

    if class_name:
        needle = _normalize_lookup(class_name)
        results = [
            spell for spell in results
            if spell.classes_json
            and any(_normalize_lookup(c) == needle for c in spell.classes_json)
        ]

    return results


def get_base_spell_by_id(*, db: Session, base_spell_id: str) -> BaseSpell | None:
    return db.exec(select(BaseSpell).where(BaseSpell.id == base_spell_id)).first()


def get_base_spell_by_canonical_key(
    *,
    db: Session,
    system: SystemType,
    canonical_key: str,
) -> BaseSpell | None:
    return db.exec(
        select(BaseSpell).where(
            BaseSpell.system == system,
            func.lower(BaseSpell.canonical_key) == _normalize_lookup(canonical_key),
        )
    ).first()


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

def _apply_payload(spell: BaseSpell, data: dict) -> None:
    db_data = _to_db_fields(data)
    for key, value in db_data.items():
        if hasattr(spell, key):
            setattr(spell, key, value)


def create_base_spell(*, db: Session, payload: BaseSpellCreate) -> BaseSpell:
    existing = get_base_spell_by_canonical_key(
        db=db,
        system=payload.system,
        canonical_key=payload.canonicalKey,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Base spell with canonical_key '{payload.canonicalKey}' already exists for system '{payload.system.value}'",
        )

    spell = BaseSpell(id=str(uuid4()), system=payload.system)
    data = payload.model_dump(exclude={"system"})
    _apply_payload(spell, data)
    db.add(spell)
    db.commit()
    db.refresh(spell)
    return spell


def update_base_spell(
    *,
    db: Session,
    spell: BaseSpell,
    payload: BaseSpellUpdate,
) -> BaseSpell:
    data = payload.model_dump(exclude_unset=True)
    _apply_payload(spell, data)
    db.add(spell)
    db.commit()
    db.refresh(spell)
    return spell


def delete_base_spell(*, db: Session, spell: BaseSpell) -> None:
    linked_campaign_spells = db.exec(
        select(CampaignSpell).where(CampaignSpell.base_spell_id == spell.id)
    ).all()
    for campaign_spell in linked_campaign_spells:
        campaign_spell.base_spell_id = None
        db.add(campaign_spell)

    aliases = db.exec(
        select(BaseSpellAlias).where(BaseSpellAlias.base_spell_id == spell.id)
    ).all()
    for alias in aliases:
        db.delete(alias)

    db.delete(spell)
    db.commit()
