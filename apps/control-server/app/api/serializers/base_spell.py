from __future__ import annotations

from app.models.base_spell import BaseSpell
from app.schemas.base_spell import BaseSpellCreate, BaseSpellRead
from app.services.combat_service.spell_automation import (
    CombatSpellAutomationMixin,
)
from app.services.combat_service.spell_automation_metadata import (
    resolve_spell_automation_metadata_from_catalog,
)


def _optional_str_attr(source: object, name: str) -> str | None:
    value = getattr(source, name, None)
    return value if isinstance(value, str) else None


def to_base_spell_read(spell: BaseSpell) -> BaseSpellRead:
    automation = resolve_spell_automation_metadata_from_catalog(
        spell,
        automation_registry=CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY,
    )
    automation_dict = automation.to_api_dict()
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
        castingTimeType=spell.casting_time_type,
        castingTime=spell.casting_time,
        rangeMeters=spell.range_meters,
        rangeText=spell.range_text,
        targetType=spell.target_type,
        selectionType=_optional_str_attr(spell, "selection_type"),
        originType=_optional_str_attr(spell, "origin_type"),
        targetAnchor=_optional_str_attr(spell, "target_anchor"),
        attackType=_optional_str_attr(spell, "attack_type"),
        rangeKind=_optional_str_attr(spell, "range_kind"),
        effectTiming=_optional_str_attr(spell, "effect_timing"),
        areaShape=spell.area_shape,
        radiusMeters=spell.radius_meters,
        lengthMeters=spell.length_meters,
        sideMeters=spell.side_meters,
        duration=spell.duration,
        componentsJson=spell.components_json,
        materialComponentText=spell.material_component_text,
        concentration=spell.concentration,
        ritual=spell.ritual,
        resolutionType=spell.resolution_type,
        savingThrow=spell.saving_throw,
        saveSuccessOutcome=spell.save_success_outcome,
        coverAppliesToSave=spell.cover_applies_to_save,
        damageDice=spell.damage_dice,
        damageType=spell.damage_type,
        healDice=spell.heal_dice,
        requiresTargetSight=spell.requires_target_sight,
        requiresTargetEffect=spell.requires_target_effect,
        requiresPointSight=spell.requires_point_sight,
        requiresPointEffect=spell.requires_point_effect,
        upcast=spell.upcast_json,
        upcastMode=spell.upcast_mode,
        upcastValue=spell.upcast_value,
        source=spell.source,
        sourceRef=spell.source_ref,
        isSrd=spell.is_srd,
        isActive=spell.is_active,
        aliases=[],
        automationMode=automation_dict["automationMode"],
        defaultSpellMode=automation_dict["defaultSpellMode"],
        requiresEffectInputs=automation_dict["requiresEffectInputs"],
        requiresMap=automation_dict["requiresMap"],
        handlerKey=automation_dict["handlerKey"],
    )


def to_base_spell_seed_entry(spell: BaseSpell) -> BaseSpellCreate:
    return BaseSpellCreate(
        system=spell.system,
        canonicalKey=spell.canonical_key,
        nameEn=spell.name_en,
        namePt=spell.name_pt,
        descriptionEn=spell.description_en,
        descriptionPt=spell.description_pt,
        level=spell.level,
        school=spell.school,
        classesJson=spell.classes_json,
        castingTimeType=spell.casting_time_type,
        castingTime=spell.casting_time,
        rangeMeters=spell.range_meters,
        rangeText=spell.range_text,
        targetType=spell.target_type,
        selectionType=_optional_str_attr(spell, "selection_type"),
        originType=_optional_str_attr(spell, "origin_type"),
        targetAnchor=_optional_str_attr(spell, "target_anchor"),
        attackType=_optional_str_attr(spell, "attack_type"),
        rangeKind=_optional_str_attr(spell, "range_kind"),
        effectTiming=_optional_str_attr(spell, "effect_timing"),
        areaShape=spell.area_shape,
        radiusMeters=spell.radius_meters,
        lengthMeters=spell.length_meters,
        sideMeters=spell.side_meters,
        duration=spell.duration,
        componentsJson=spell.components_json,
        materialComponentText=spell.material_component_text,
        concentration=spell.concentration,
        ritual=spell.ritual,
        resolutionType=spell.resolution_type,
        savingThrow=spell.saving_throw,
        saveSuccessOutcome=spell.save_success_outcome,
        coverAppliesToSave=spell.cover_applies_to_save,
        damageDice=spell.damage_dice,
        damageType=spell.damage_type,
        healDice=spell.heal_dice,
        requiresTargetSight=spell.requires_target_sight,
        requiresTargetEffect=spell.requires_target_effect,
        requiresPointSight=spell.requires_point_sight,
        requiresPointEffect=spell.requires_point_effect,
        upcast=spell.upcast_json,
        source=spell.source,
        sourceRef=spell.source_ref,
        isSrd=spell.is_srd,
        isActive=spell.is_active,
    )
