from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.base_spell import BaseSpell, SpellSchool, SpellSource
from app.models.campaign_spell import CampaignSpell
from app.models.campaign import Campaign, SystemType
from app.schemas.base_spell import BaseSpellCreate


def _normalize_lookup(value: str) -> str:
    return value.strip().lower()


_FIELD_MAP: dict[str, str] = {
    "canonicalKey": "canonical_key",
    "nameEn": "name_en",
    "namePt": "name_pt",
    "descriptionEn": "description_en",
    "descriptionPt": "description_pt",
    "classesJson": "classes_json",
    "castingTimeType": "casting_time_type",
    "castingTime": "casting_time",
    "rangeMeters": "range_meters",
    "rangeText": "range_text",
    "targetType": "target_type",
    "maxTargets": "max_targets",
    "selectionType": "selection_type",
    "originType": "origin_type",
    "targetAnchor": "target_anchor",
    "attackType": "attack_type",
    "rangeKind": "range_kind",
    "effectTiming": "effect_timing",
    "areaShape": "area_shape",
    "radiusMeters": "radius_meters",
    "lengthMeters": "length_meters",
    "sideMeters": "side_meters",
    "componentsJson": "components_json",
    "materialComponentText": "material_component_text",
    "resolutionType": "resolution_type",
    "savingThrow": "saving_throw",
    "saveSuccessOutcome": "save_success_outcome",
    "coverAppliesToSave": "cover_applies_to_save",
    "damageDice": "damage_dice",
    "damageType": "damage_type",
    "healDice": "heal_dice",
    "effects": "effects_json",
    "attackAdvantageCondition": "attack_advantage_condition_json",
    "onEndEffects": "on_end_effects_json",
    "variants": "variants_json",
    "persistentArea": "persistent_area_json",
    "requiresTargetSight": "requires_target_sight",
    "requiresTargetEffect": "requires_target_effect",
    "requiresPointSight": "requires_point_sight",
    "requiresPointEffect": "requires_point_effect",
    "upcast": "upcast_json",
    "upcastMode": "upcast_mode",
    "upcastValue": "upcast_value",
    "cantripScaling": "cantrip_scaling_json",
    "sourceRef": "source_ref",
    "isSrd": "is_srd",
    "outOfCombatCastable": "out_of_combat_castable",
    "outOfCombatTarget": "out_of_combat_target",
}


def _to_db_fields(data: dict) -> dict:
    return {_FIELD_MAP.get(key, key): value for key, value in data.items()}


def _apply_spell_data(spell: CampaignSpell, data: dict) -> None:
    for key, value in _to_db_fields(data).items():
        if hasattr(spell, key):
            setattr(spell, key, value)


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
                target_type=base_spell.target_type,
                max_targets=base_spell.max_targets,
                selection_type=base_spell.selection_type,
                origin_type=base_spell.origin_type,
                target_anchor=base_spell.target_anchor,
                attack_type=base_spell.attack_type,
                range_kind=base_spell.range_kind,
                effect_timing=base_spell.effect_timing,
                area_shape=base_spell.area_shape,
                radius_meters=base_spell.radius_meters,
                length_meters=base_spell.length_meters,
                side_meters=base_spell.side_meters,
                duration=base_spell.duration,
                components_json=base_spell.components_json,
                material_component_text=base_spell.material_component_text,
                concentration=base_spell.concentration,
                ritual=base_spell.ritual,
                resolution_type=base_spell.resolution_type,
                damage_dice=base_spell.damage_dice,
                damage_type=base_spell.damage_type,
                heal_dice=base_spell.heal_dice,
                effects_json=base_spell.effects_json,
                attack_advantage_condition_json=base_spell.attack_advantage_condition_json,
                on_end_effects_json=base_spell.on_end_effects_json,
                variants_json=base_spell.variants_json,
                persistent_area_json=base_spell.persistent_area_json,
                saving_throw=base_spell.saving_throw,
                save_success_outcome=base_spell.save_success_outcome,
                upcast_json=base_spell.upcast_json,
                upcast_mode=base_spell.upcast_mode,
                upcast_value=base_spell.upcast_value,
                cantrip_scaling_json=base_spell.cantrip_scaling_json,
                requires_target_sight=base_spell.requires_target_sight,
                requires_target_effect=base_spell.requires_target_effect,
                requires_point_sight=base_spell.requires_point_sight,
                requires_point_effect=base_spell.requires_point_effect,
                source=base_spell.source,
                source_ref=base_spell.source_ref,
                is_srd=base_spell.is_srd,
                out_of_combat_castable=base_spell.out_of_combat_castable,
                out_of_combat_target=base_spell.out_of_combat_target,
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


def get_campaign_spell_by_canonical_key(
    *,
    db: Session,
    campaign_id: str,
    canonical_key: str,
) -> CampaignSpell | None:
    return db.exec(
        select(CampaignSpell).where(
            CampaignSpell.campaign_id == campaign_id,
            func.lower(CampaignSpell.canonical_key) == _normalize_lookup(canonical_key),
        )
    ).first()


def create_campaign_spell(
    *,
    db: Session,
    campaign: Campaign,
    payload: BaseSpellCreate,
    commit: bool = True,
    refresh: bool = True,
) -> CampaignSpell:
    existing = get_campaign_spell_by_canonical_key(
        db=db,
        campaign_id=campaign.id,
        canonical_key=payload.canonicalKey,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Campaign spell with canonical_key '{payload.canonicalKey}' "
                f"already exists for campaign '{campaign.id}'"
            ),
        )

    spell = CampaignSpell(
        id=str(uuid4()),
        campaign_id=campaign.id,
        base_spell_id=None,
        is_custom=True,
        is_enabled=True,
        source=payload.source or SpellSource.ADMIN_PANEL.value,
    )
    _apply_spell_data(spell, payload.model_dump(exclude={"system"}))
    if not spell.source:
        spell.source = SpellSource.ADMIN_PANEL.value

    db.add(spell)
    if commit:
        db.commit()
    else:
        db.flush()
    if refresh:
        db.refresh(spell)
    return spell


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

    _apply_spell_data(spell, data)

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
