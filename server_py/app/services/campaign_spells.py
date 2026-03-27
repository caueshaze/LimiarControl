from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_spell import BaseSpell
from app.models.campaign_spell import CampaignSpell
from app.models.campaign import Campaign, SystemType
from app.models.base_spell import SpellSchool


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


def seed_campaign_spells(
    *,
    db: Session,
    campaign_id: str,
    system: SystemType,
    commit: bool = True,
) -> int:
    existing_count = db.exec(
        select(func.count())
        .select_from(CampaignSpell)
        .where(CampaignSpell.campaign_id == campaign_id)
    ).one()
    if existing_count:
        return 0

    base_spells = db.exec(
        select(BaseSpell)
        .where(
            BaseSpell.system == system,
            BaseSpell.is_active == True,  # noqa: E712
        )
        .order_by(BaseSpell.level, BaseSpell.name_en)
    ).all()

    inserted = 0
    for base_spell in base_spells:
        db.add(
            CampaignSpell(
                campaign_id=campaign_id,
                base_spell_id=base_spell.id,
                canonical_key=base_spell.canonical_key,
                name_en=base_spell.name_en,
                name_pt=base_spell.name_pt,
                description_en=base_spell.description_en,
                description_pt=base_spell.description_pt,
                level=base_spell.level,
                school=base_spell.school,
                classes_json=base_spell.classes_json,
                casting_time_type=base_spell.casting_time_type,
                casting_time=base_spell.casting_time,
                range_meters=base_spell.range_meters,
                range_text=base_spell.range_text,
                target_mode=base_spell.target_mode,
                duration=base_spell.duration,
                components_json=base_spell.components_json,
                material_component_text=base_spell.material_component_text,
                concentration=base_spell.concentration,
                ritual=base_spell.ritual,
                resolution_type=base_spell.resolution_type,
                damage_dice=base_spell.damage_dice,
                damage_type=base_spell.damage_type,
                heal_dice=base_spell.heal_dice,
                saving_throw=base_spell.saving_throw,
                save_success_outcome=base_spell.save_success_outcome,
                upcast_mode=base_spell.upcast_mode,
                upcast_value=base_spell.upcast_value,
                source=base_spell.source,
                source_ref=base_spell.source_ref,
                is_srd=base_spell.is_srd,
                is_custom=False,
                is_enabled=True,
            )
        )
        inserted += 1

    if commit and inserted:
        db.commit()

    return inserted


def snapshot_campaign_spells(
    *,
    campaign: Campaign,
    db: Session,
    commit: bool = True,
) -> int:
    """Freeze the campaign spell catalog against the current base catalog state."""
    if not campaign.id:
        raise ValueError("Campaign must have an id before spell snapshotting")

    if campaign.spell_catalog_snapshot_at is not None:
        return db.exec(
            select(func.count())
            .select_from(CampaignSpell)
            .where(CampaignSpell.campaign_id == campaign.id)
        ).one()

    inserted = seed_campaign_spells(
        db=db,
        campaign_id=campaign.id,
        system=campaign.system,
        commit=False,
    )
    campaign.spell_catalog_snapshot_at = datetime.now(timezone.utc)
    db.add(campaign)

    if commit:
        db.commit()
        db.refresh(campaign)

    return inserted


def list_campaign_spells(
    *,
    db: Session,
    campaign_id: str,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = None,
    canonical_key: str | None = None,
) -> list[CampaignSpell]:
    statement = (
        select(CampaignSpell)
        .where(
            CampaignSpell.campaign_id == campaign_id,
            CampaignSpell.is_enabled == True,  # noqa: E712
        )
        .order_by(CampaignSpell.level, CampaignSpell.name_en)
    )
    if level is not None:
        statement = statement.where(CampaignSpell.level == level)
    if school is not None:
        statement = statement.where(CampaignSpell.school == school)
    if canonical_key:
        statement = statement.where(
            func.lower(CampaignSpell.canonical_key) == _normalize_lookup(canonical_key)
        )

    results = list(db.exec(statement).all())
    if class_name:
        needle = _normalize_lookup(class_name)
        results = [
            spell
            for spell in results
            if spell.classes_json
            and any(_normalize_lookup(entry) == needle for entry in spell.classes_json)
        ]
    return results


def get_campaign_spell_by_id(
    *,
    db: Session,
    campaign_id: str,
    campaign_spell_id: str,
) -> CampaignSpell | None:
    return db.exec(
        select(CampaignSpell).where(
            CampaignSpell.id == campaign_spell_id,
            CampaignSpell.campaign_id == campaign_id,
        )
    ).first()


def update_campaign_spell(
    *,
    db: Session,
    campaign_id: str,
    campaign_spell_id: str,
    data: dict,
) -> CampaignSpell | None:
    spell = get_campaign_spell_by_id(
        db=db,
        campaign_id=campaign_id,
        campaign_spell_id=campaign_spell_id,
    )
    if not spell:
        return None

    for key, value in data.items():
        if hasattr(spell, key):
            setattr(spell, key, value)

    db.add(spell)
    db.commit()
    db.refresh(spell)
    return spell


def disable_campaign_spell(
    *,
    db: Session,
    campaign_id: str,
    campaign_spell_id: str,
) -> bool:
    spell = get_campaign_spell_by_id(
        db=db,
        campaign_id=campaign_id,
        campaign_spell_id=campaign_spell_id,
    )
    if not spell:
        return False

    spell.is_enabled = False
    db.add(spell)
    db.commit()
    return True
