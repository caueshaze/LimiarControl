from __future__ import annotations

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_spell import BaseSpell, SpellSchool
from app.models.campaign import SystemType


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


def list_base_spells(
    *,
    db: Session,
    system: SystemType | None = None,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = None,
    canonical_key: str | None = None,
) -> list[BaseSpell]:
    statement = select(BaseSpell).where(BaseSpell.is_active == True)  # noqa: E712
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


def update_base_spell(
    *,
    db: Session,
    base_spell_id: str,
    data: dict,
) -> BaseSpell | None:
    spell = db.exec(select(BaseSpell).where(BaseSpell.id == base_spell_id)).first()
    if not spell:
        return None
    for key, value in data.items():
        if hasattr(spell, key):
            setattr(spell, key, value)
    db.add(spell)
    db.commit()
    db.refresh(spell)
    return spell


def delete_base_spell(*, db: Session, base_spell_id: str) -> bool:
    spell = db.exec(select(BaseSpell).where(BaseSpell.id == base_spell_id)).first()
    if not spell:
        return False
    db.delete(spell)
    db.commit()
    return True
