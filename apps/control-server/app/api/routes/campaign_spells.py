from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.base_spell import SpellSchool
from app.models.campaign import Campaign
from app.models.campaign_spell import CampaignSpell
from app.models.user import User
from app.schemas.base_spell import BaseSpellCreate, BaseSpellRead, BaseSpellUpdate
from app.services.campaign_spells import (
    create_campaign_spell,
    disable_campaign_spell,
    get_campaign_spell_by_id,
    list_campaign_spells,
    update_campaign_spell,
)
from app.services.combat_service.spell_automation import (
    CombatSpellAutomationMixin,
)
from app.services.combat_service.spell_automation_metadata import (
    resolve_spell_automation_metadata_from_catalog,
)

router = APIRouter()


def _optional_str_attr(source: object, name: str) -> str | None:
    value = getattr(source, name, None)
    return value if isinstance(value, str) else None


def to_campaign_spell_read(
    spell: CampaignSpell,
    campaign: Campaign,
) -> BaseSpellRead:
    automation = resolve_spell_automation_metadata_from_catalog(
        spell,
        automation_registry=CombatSpellAutomationMixin._SPELL_AUTOMATION_REGISTRY,
    )
    automation_dict = automation.to_api_dict()
    return BaseSpellRead(
        id=spell.id,
        system=campaign.system,
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
        maxTargets=spell.max_targets,
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
        damageDice=spell.damage_dice,
        damageType=spell.damage_type,
        healDice=spell.heal_dice,
        effects=spell.effects_json,
        onEndEffects=spell.on_end_effects_json,
        variants=spell.variants_json,
        persistentArea=spell.persistent_area_json,
        savingThrow=spell.saving_throw,
        saveSuccessOutcome=spell.save_success_outcome,
        coverAppliesToSave=spell.cover_applies_to_save,
        upcast=spell.upcast_json if spell.level > 0 else None,
        upcastMode=spell.upcast_mode,
        upcastValue=spell.upcast_value,
        cantripScaling=spell.cantrip_scaling_json,
        requiresTargetSight=spell.requires_target_sight,
        requiresTargetEffect=spell.requires_target_effect,
        requiresPointSight=spell.requires_point_sight,
        requiresPointEffect=spell.requires_point_effect,
        source=spell.source,
        sourceRef=spell.source_ref,
        isSrd=spell.is_srd,
        isActive=spell.is_enabled,
        outOfCombatCastable=spell.out_of_combat_castable,
        outOfCombatTarget=spell.out_of_combat_target,
        aliases=[],
        automationMode=automation_dict["automationMode"],
        defaultSpellMode=automation_dict["defaultSpellMode"],
        requiresEffectInputs=automation_dict["requiresEffectInputs"],
        requiresMap=automation_dict["requiresMap"],
        handlerKey=automation_dict["handlerKey"],
    )




@router.get("/{campaign_id}/spells", response_model=list[BaseSpellRead])
def list_spells(
    campaign_id: str,
    level: int | None = None,
    school: SpellSchool | None = None,
    class_name: str | None = Query(None, alias="class_name"),
    canonical_key: str | None = None,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_campaign_member(campaign_id, user, session)
    spells = list_campaign_spells(
        db=session,
        campaign_id=campaign_id,
        level=level,
        school=school,
        class_name=class_name,
        canonical_key=canonical_key,
    )
    return [to_campaign_spell_read(spell, campaign) for spell in spells]


@router.get("/{campaign_id}/spells/{campaign_spell_id}", response_model=BaseSpellRead)
def get_spell(
    campaign_id: str,
    campaign_spell_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_campaign_member(campaign_id, user, session)
    spell = get_campaign_spell_by_id(
        db=session,
        campaign_id=campaign_id,
        campaign_spell_id=campaign_spell_id,
    )
    if not spell or not spell.is_enabled:
        raise HTTPException(status_code=404, detail="Campaign spell not found")
    return to_campaign_spell_read(spell, campaign)


@router.post("/{campaign_id}/spells", response_model=BaseSpellRead, status_code=201)
def create_spell(
    campaign_id: str,
    payload: BaseSpellCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    spell = create_campaign_spell(
        db=session,
        campaign=campaign,
        payload=payload,
    )
    return to_campaign_spell_read(spell, campaign)


@router.put("/{campaign_id}/spells/{campaign_spell_id}", response_model=BaseSpellRead)
def update_spell(
    campaign_id: str,
    campaign_spell_id: str,
    payload: BaseSpellUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    campaign, _member = require_gm(campaign_id, user, session)
    field_map = {
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
        "duration": "duration",
        "componentsJson": "components_json",
        "materialComponentText": "material_component_text",
        "resolutionType": "resolution_type",
        "damageDice": "damage_dice",
        "damageType": "damage_type",
        "healDice": "heal_dice",
        "effects": "effects_json",
        "onEndEffects": "on_end_effects_json",
        "variants": "variants_json",
        "persistentArea": "persistent_area_json",
        "savingThrow": "saving_throw",
        "saveSuccessOutcome": "save_success_outcome",
        "coverAppliesToSave": "cover_applies_to_save",
        "upcast": "upcast_json",
        "upcastMode": "upcast_mode",
        "upcastValue": "upcast_value",
        "cantripScaling": "cantrip_scaling_json",
        "requiresTargetSight": "requires_target_sight",
        "requiresTargetEffect": "requires_target_effect",
        "requiresPointSight": "requires_point_sight",
        "requiresPointEffect": "requires_point_effect",
        "outOfCombatTarget": "out_of_combat_target",
    }
    data = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        data[field_map.get(key, key)] = value

    spell = update_campaign_spell(
        db=session,
        campaign_id=campaign_id,
        campaign_spell_id=campaign_spell_id,
        data=data,
    )
    if not spell:
        raise HTTPException(status_code=404, detail="Campaign spell not found")

    return to_campaign_spell_read(spell, campaign)


@router.delete("/{campaign_id}/spells/{campaign_spell_id}", status_code=204)
def delete_spell(
    campaign_id: str,
    campaign_spell_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    deleted = disable_campaign_spell(
        db=session,
        campaign_id=campaign_id,
        campaign_spell_id=campaign_spell_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaign spell not found")
    return None
