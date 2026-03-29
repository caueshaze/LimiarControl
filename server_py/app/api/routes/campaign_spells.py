from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.base_spell import SpellSchool
from app.models.campaign import Campaign
from app.models.campaign_spell import CampaignSpell
from app.models.user import User
from app.schemas.base_spell import BaseSpellRead, BaseSpellUpdate
from app.services.campaign_spells import (
    disable_campaign_spell,
    get_campaign_spell_by_id,
    list_campaign_spells,
    update_campaign_spell,
)

router = APIRouter()


def to_campaign_spell_read(
    spell: CampaignSpell,
    campaign: Campaign,
) -> BaseSpellRead:
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
        targetMode=spell.target_mode,
        duration=spell.duration,
        componentsJson=spell.components_json,
        materialComponentText=spell.material_component_text,
        concentration=spell.concentration,
        ritual=spell.ritual,
        resolutionType=spell.resolution_type,
        damageDice=spell.damage_dice,
        damageType=spell.damage_type,
        healDice=spell.heal_dice,
        savingThrow=spell.saving_throw,
        saveSuccessOutcome=spell.save_success_outcome,
        upcast=spell.upcast_json,
        upcastMode=spell.upcast_mode,
        upcastValue=spell.upcast_value,
        source=spell.source,
        sourceRef=spell.source_ref,
        isSrd=spell.is_srd,
        isActive=spell.is_enabled,
        aliases=[],
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
        "targetMode": "target_mode",
        "duration": "duration",
        "componentsJson": "components_json",
        "materialComponentText": "material_component_text",
        "resolutionType": "resolution_type",
        "damageDice": "damage_dice",
        "damageType": "damage_type",
        "healDice": "heal_dice",
        "savingThrow": "saving_throw",
        "saveSuccessOutcome": "save_success_outcome",
        "upcast": "upcast_json",
        "upcastMode": "upcast_mode",
        "upcastValue": "upcast_value",
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
