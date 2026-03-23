from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.campaign_entity import CampaignEntity
from app.models.session import Session as SessionModel, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.user import User
from app.schemas.campaign_entity import (
    VALID_CATEGORIES,
    CombatAction,
    AbilityScores,
    CampaignEntityCreate,
    CampaignEntityPublicRead,
    CampaignEntityRead,
    CampaignEntityUpdate,
    EntitySenses,
    EntitySpellcasting,
)

router = APIRouter()


def _model_to_dict(value: BaseModel | None) -> dict | None:
    if value is None:
        return None
    dumped = value.model_dump(exclude_none=True)
    return dumped if dumped else None


def _dict_to_model(raw: dict | None, model_cls: type[BaseModel]) -> BaseModel | None:
    if not raw:
        return None
    return model_cls(**raw)


def _combat_actions_to_list(actions: list[CombatAction] | None) -> list[dict] | None:
    if not actions:
        return None
    dumped = [action.model_dump(exclude_none=True) for action in actions]
    return dumped or None


def _list_to_combat_actions(raw: list | None) -> list[CombatAction]:
    if not raw:
        return []
    return [CombatAction(**entry) for entry in raw if isinstance(entry, dict)]


def _mapping_to_dict(raw: dict | None) -> dict:
    return raw if isinstance(raw, dict) else {}


def _string_list(raw: list | None) -> list[str]:
    if not raw:
        return []
    return [entry for entry in raw if isinstance(entry, str)]


def to_campaign_entity_read(entry: CampaignEntity) -> CampaignEntityRead:
    return CampaignEntityRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        name=entry.name,
        category=entry.category,
        size=entry.size,
        creatureType=entry.creature_type,
        creatureSubtype=entry.creature_subtype,
        description=entry.description,
        imageUrl=entry.image_url,
        armorClass=entry.armor_class,
        maxHp=entry.max_hp,
        speedMeters=entry.speed_meters,
        initiativeBonus=entry.initiative_bonus,
        abilities=_dict_to_model(entry.abilities, AbilityScores) or AbilityScores(),
        savingThrows=_mapping_to_dict(entry.saving_throws),
        skills=_mapping_to_dict(entry.skills),
        senses=_dict_to_model(entry.senses, EntitySenses),
        spellcasting=_dict_to_model(entry.spellcasting, EntitySpellcasting),
        damageResistances=_string_list(entry.damage_resistances),
        damageImmunities=_string_list(entry.damage_immunities),
        damageVulnerabilities=_string_list(entry.damage_vulnerabilities),
        conditionImmunities=_string_list(entry.condition_immunities),
        combatActions=_list_to_combat_actions(entry.combat_actions),
        actions=entry.actions,
        notesPrivate=entry.notes_private,
        notesPublic=entry.notes_public,
        createdAt=entry.created_at,
        updatedAt=entry.updated_at,
    )


def to_campaign_entity_public_read(entry: CampaignEntity) -> CampaignEntityPublicRead:
    return CampaignEntityPublicRead(
        id=entry.id,
        campaignId=entry.campaign_id,
        name=entry.name,
        category=entry.category,
        size=entry.size,
        creatureType=entry.creature_type,
        creatureSubtype=entry.creature_subtype,
        description=entry.description,
        imageUrl=entry.image_url,
        armorClass=entry.armor_class,
        maxHp=entry.max_hp,
        speedMeters=entry.speed_meters,
        initiativeBonus=entry.initiative_bonus,
        abilities=_dict_to_model(entry.abilities, AbilityScores) or AbilityScores(),
        savingThrows=_mapping_to_dict(entry.saving_throws),
        skills=_mapping_to_dict(entry.skills),
        senses=_dict_to_model(entry.senses, EntitySenses),
        spellcasting=_dict_to_model(entry.spellcasting, EntitySpellcasting),
        damageResistances=_string_list(entry.damage_resistances),
        damageImmunities=_string_list(entry.damage_immunities),
        damageVulnerabilities=_string_list(entry.damage_vulnerabilities),
        conditionImmunities=_string_list(entry.condition_immunities),
        combatActions=_list_to_combat_actions(entry.combat_actions),
        actions=entry.actions,
        notesPublic=entry.notes_public,
        createdAt=entry.created_at,
    )


@router.get("/{campaign_id}/entities", response_model=list[CampaignEntityRead])
def list_campaign_entities(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    statement = (
        select(CampaignEntity)
        .where(CampaignEntity.campaign_id == campaign_id)
        .order_by(CampaignEntity.created_at.desc())
    )
    entries = session.exec(statement).all()
    return [to_campaign_entity_read(e) for e in entries]


@router.post("/{campaign_id}/entities", response_model=CampaignEntityRead, status_code=201)
def create_campaign_entity(
    campaign_id: str,
    payload: CampaignEntityCreate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    entry = CampaignEntity(
        id=str(uuid4()),
        campaign_id=campaign_id,
        name=payload.name.strip(),
        category=payload.category,
        size=payload.size,
        creature_type=payload.creatureType,
        creature_subtype=payload.creatureSubtype,
        description=payload.description,
        image_url=payload.imageUrl,
        armor_class=payload.armorClass,
        max_hp=payload.maxHp,
        speed_meters=payload.speedMeters,
        initiative_bonus=payload.initiativeBonus,
        abilities=_model_to_dict(payload.abilities),
        saving_throws=payload.savingThrows or None,
        skills=payload.skills or None,
        senses=_model_to_dict(payload.senses),
        spellcasting=_model_to_dict(payload.spellcasting),
        damage_resistances=payload.damageResistances or None,
        damage_immunities=payload.damageImmunities or None,
        damage_vulnerabilities=payload.damageVulnerabilities or None,
        condition_immunities=payload.conditionImmunities or None,
        combat_actions=_combat_actions_to_list(payload.combatActions),
        actions=payload.actions,
        notes_private=payload.notesPrivate,
        notes_public=payload.notesPublic,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_campaign_entity_read(entry)


@router.put("/{campaign_id}/entities/{entity_id}", response_model=CampaignEntityRead)
def update_campaign_entity(
    campaign_id: str,
    entity_id: str,
    payload: CampaignEntityUpdate,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == entity_id,
            CampaignEntity.campaign_id == campaign_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entity not found")
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if payload.category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")
    entry.name = payload.name.strip()
    entry.category = payload.category
    entry.size = payload.size
    entry.creature_type = payload.creatureType
    entry.creature_subtype = payload.creatureSubtype
    entry.description = payload.description
    entry.image_url = payload.imageUrl
    entry.armor_class = payload.armorClass
    entry.max_hp = payload.maxHp
    entry.speed_meters = payload.speedMeters
    entry.initiative_bonus = payload.initiativeBonus
    entry.abilities = _model_to_dict(payload.abilities)
    entry.saving_throws = payload.savingThrows or None
    entry.skills = payload.skills or None
    entry.senses = _model_to_dict(payload.senses)
    entry.spellcasting = _model_to_dict(payload.spellcasting)
    entry.damage_resistances = payload.damageResistances or None
    entry.damage_immunities = payload.damageImmunities or None
    entry.damage_vulnerabilities = payload.damageVulnerabilities or None
    entry.condition_immunities = payload.conditionImmunities or None
    entry.combat_actions = _combat_actions_to_list(payload.combatActions)
    entry.actions = payload.actions
    entry.notes_private = payload.notesPrivate
    entry.notes_public = payload.notesPublic
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return to_campaign_entity_read(entry)


@router.delete("/{campaign_id}/entities/{entity_id}", status_code=204)
def delete_campaign_entity(
    campaign_id: str,
    entity_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_gm(campaign_id, user, session)
    entry = session.exec(
        select(CampaignEntity).where(
            CampaignEntity.id == entity_id,
            CampaignEntity.campaign_id == campaign_id,
        )
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entity not found")
    session.delete(entry)
    session.commit()
    return None


@router.get("/{campaign_id}/entities/public", response_model=list[CampaignEntityPublicRead])
def list_public_campaign_entities(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    require_campaign_member(campaign_id, user, session)
    # Return campaign entities that are currently revealed in any active session
    statement = (
        select(CampaignEntity)
        .join(SessionEntity, SessionEntity.campaign_entity_id == CampaignEntity.id)
        .join(SessionModel, SessionModel.id == SessionEntity.session_id)
        .where(
            CampaignEntity.campaign_id == campaign_id,
            SessionEntity.visible_to_players == True,
            SessionModel.status == SessionStatus.ACTIVE,
        )
        .distinct()
    )
    entries = session.exec(statement).all()
    return [to_campaign_entity_public_read(e) for e in entries]
