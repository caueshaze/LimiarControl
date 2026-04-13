"""Authoritative roll resolution endpoints.

These endpoints resolve d20 rolls (ability, save, skill, initiative, attack-base),
log the result, and publish a realtime event.  They do NOT mutate HP, status, or turns.
"""

from __future__ import annotations

from math import floor

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session as DbSession, select

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models.campaign import RoleMode
from app.models.campaign_entity import CampaignEntity
from app.models.campaign_member import CampaignMember
from app.models.session import Session, SessionStatus
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity_shared import SKILL_ABILITY_MAP, ability_modifier
from app.models.user import User
from app.schemas.roll import (
    AbilityRollRequest,
    AttackBaseRollRequest,
    InitiativeRollRequest,
    RollActorStats,
    RollResult,
    SaveRollRequest,
    SkillRollRequest,
)
from app.services.centrifugo import centrifugo
from app.services.realtime import build_event, campaign_channel, event_version, session_channel
from app.services.combat import CombatService
from app.services.roll_resolution import (
    resolve_ability_check,
    resolve_attack_base,
    resolve_initiative,
    resolve_saving_throw,
    resolve_skill_check,
)

from ._shared import record_session_activity

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_session_and_member(
    session_id: str, user: User, db: DbSession
) -> tuple[Session, CampaignMember]:
    entry = db.exec(select(Session).where(Session.id == session_id)).first()
    if not entry:
        raise HTTPException(404, "Session not found")
    if entry.status != SessionStatus.ACTIVE:
        raise HTTPException(400, "Session is not active")
    member = db.exec(
        select(CampaignMember).where(
            CampaignMember.campaign_id == entry.campaign_id,
            CampaignMember.user_id == user.id,
        )
    ).first()
    if not member:
        raise HTTPException(403, "Not a campaign member")
    return entry, member


def _authorize_roll(
    member: CampaignMember, actor_kind: str, actor_ref_id: str, user_id: str
) -> bool:
    """Returns True if GM, False if player rolling for self.  Raises 403 otherwise."""
    is_gm = member.role_mode == RoleMode.GM
    if is_gm:
        return True
    if actor_kind == "player" and actor_ref_id == user_id:
        return False  # not a GM roll
    raise HTTPException(403, "You can only roll for your own character")


def _build_player_stats(
    db: DbSession, session_id: str, player_user_id: str
) -> RollActorStats:
    state = db.exec(
        select(SessionState).where(
            SessionState.session_id == session_id,
            SessionState.player_user_id == player_user_id,
        )
    ).first()
    if not state:
        raise HTTPException(404, "Player state not found for this session")
    data = state.state_json if isinstance(state.state_json, dict) else {}
    abilities = data.get("abilities") if isinstance(data.get("abilities"), dict) else {}
    level = data.get("level", 1) if isinstance(data.get("level"), int) else 1
    prof = floor((level - 1) / 4) + 2

    # Build saving throw bonuses from proficiency booleans
    save_profs = data.get("savingThrowProficiencies")
    save_profs = save_profs if isinstance(save_profs, dict) else {}
    saving_throws: dict[str, int] = {}
    for ab in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
        bonus = ability_modifier(abilities.get(ab, 10))
        if save_profs.get(ab) is True:
            bonus += prof
        saving_throws[ab] = bonus

    # Build skill bonuses from proficiency levels (0, 0.5, 1, 2)
    skill_profs = data.get("skillProficiencies")
    skill_profs = skill_profs if isinstance(skill_profs, dict) else {}
    skills: dict[str, int] = {}
    for skill_name, base_ability in SKILL_ABILITY_MAP.items():
        bonus = ability_modifier(abilities.get(base_ability, 10))
        prof_level = skill_profs.get(skill_name, 0)
        if isinstance(prof_level, (int, float)) and prof_level > 0:
            bonus += floor(prof * prof_level)
        skills[skill_name] = bonus

    return RollActorStats(
        display_name=data.get("characterName") or "Player",
        abilities=abilities,
        saving_throws=saving_throws,
        skills=skills,
        initiative_bonus=None,
        proficiency_bonus=prof,
        actor_kind="player",
        actor_ref_id=player_user_id,
    )


def _build_entity_stats(db: DbSession, session_entity_id: str) -> RollActorStats:
    se = db.exec(select(SessionEntity).where(SessionEntity.id == session_entity_id)).first()
    if not se:
        raise HTTPException(404, "Session entity not found")
    ce = db.exec(select(CampaignEntity).where(CampaignEntity.id == se.campaign_entity_id)).first()
    if not ce:
        raise HTTPException(404, "Campaign entity not found")

    abilities_raw = ce.abilities if isinstance(ce.abilities, dict) else {}
    overrides = se.overrides if isinstance(se.overrides, dict) else {}

    # Merge abilities with overrides
    override_abilities = overrides.get("abilities") if isinstance(overrides.get("abilities"), dict) else {}
    abilities = {**abilities_raw, **override_abilities}

    # Merge saving throws
    base_saves = ce.saving_throws if isinstance(ce.saving_throws, dict) else {}
    override_saves = overrides.get("savingThrows") if isinstance(overrides.get("savingThrows"), dict) else {}
    saving_throws = {**base_saves, **override_saves} if (base_saves or override_saves) else None

    # Merge skills
    base_skills = ce.skills if isinstance(ce.skills, dict) else {}
    override_skills = overrides.get("skills") if isinstance(overrides.get("skills"), dict) else {}
    skills = {**base_skills, **override_skills} if (base_skills or override_skills) else None

    initiative_bonus = overrides.get("initiativeBonus", ce.initiative_bonus)
    if not isinstance(initiative_bonus, int):
        initiative_bonus = None

    return RollActorStats(
        display_name=se.label or ce.name or "Entity",
        abilities=abilities,
        saving_throws=saving_throws,
        skills=skills,
        initiative_bonus=initiative_bonus,
        proficiency_bonus=2,
        actor_kind="session_entity",
        actor_ref_id=session_entity_id,
    )


def _build_actor_stats(
    db: DbSession, session_id: str, actor_kind: str, actor_ref_id: str
) -> RollActorStats:
    if actor_kind == "player":
        return _build_player_stats(db, session_id, actor_ref_id)
    return _build_entity_stats(db, actor_ref_id)


async def _publish_and_log(
    entry: Session, member: CampaignMember, user: User, result: RollResult, db: DbSession
) -> None:
    payload = result.model_dump(mode="json")
    payload["partyId"] = entry.party_id

    await centrifugo.publish(
        session_channel(entry.id),
        build_event("roll_resolved", payload, version=event_version(result.timestamp)),
    )
    await centrifugo.publish(
        campaign_channel(entry.campaign_id),
        build_event("roll_resolved", payload, version=event_version(result.timestamp)),
    )

    record_session_activity(
        entry,
        "roll_resolved",
        db,
        member_id=member.id,
        user_id=user.id,
        actor_name=member.display_name,
        payload=payload,
        created_at=result.timestamp,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions/{session_id}/rolls/ability", response_model=RollResult)
async def roll_ability(
    session_id: str,
    body: AbilityRollRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
):
    entry, member = _get_session_and_member(session_id, user, db)
    is_gm = _authorize_roll(member, body.actor_kind, body.actor_ref_id, user.id)
    stats = _build_actor_stats(db, session_id, body.actor_kind, body.actor_ref_id)

    result = resolve_ability_check(
        stats, body.ability, body.advantage_mode, body.bonus_override, body.dc,
        body.roll_source, body.manual_roll, body.manual_rolls,
    )
    result.is_gm_roll = is_gm
    result.roll_source = body.roll_source

    await _publish_and_log(entry, member, user, result, db)
    return result


@router.post("/sessions/{session_id}/rolls/save", response_model=RollResult)
async def roll_save(
    session_id: str,
    body: SaveRollRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
):
    entry, member = _get_session_and_member(session_id, user, db)
    is_gm = _authorize_roll(member, body.actor_kind, body.actor_ref_id, user.id)
    stats = _build_actor_stats(db, session_id, body.actor_kind, body.actor_ref_id)

    result = resolve_saving_throw(
        stats, body.ability, body.advantage_mode, body.bonus_override, body.dc,
        body.roll_source, body.manual_roll, body.manual_rolls,
    )
    result.is_gm_roll = is_gm
    result.roll_source = body.roll_source

    await _publish_and_log(entry, member, user, result, db)
    return result


@router.post("/sessions/{session_id}/rolls/skill", response_model=RollResult)
async def roll_skill(
    session_id: str,
    body: SkillRollRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
):
    entry, member = _get_session_and_member(session_id, user, db)
    is_gm = _authorize_roll(member, body.actor_kind, body.actor_ref_id, user.id)
    stats = _build_actor_stats(db, session_id, body.actor_kind, body.actor_ref_id)

    result = resolve_skill_check(
        stats, body.skill, body.advantage_mode, body.bonus_override, body.dc,
        body.roll_source, body.manual_roll, body.manual_rolls,
    )
    result.is_gm_roll = is_gm
    result.roll_source = body.roll_source

    await _publish_and_log(entry, member, user, result, db)
    return result


@router.post("/sessions/{session_id}/rolls/initiative", response_model=RollResult)
async def roll_initiative(
    session_id: str,
    body: InitiativeRollRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
):
    entry, member = _get_session_and_member(session_id, user, db)
    is_gm = _authorize_roll(member, body.actor_kind, body.actor_ref_id, user.id)
    stats = _build_actor_stats(db, session_id, body.actor_kind, body.actor_ref_id)

    result = resolve_initiative(
        stats, body.advantage_mode, body.bonus_override,
        body.roll_source, body.manual_roll, body.manual_rolls,
    )
    result.is_gm_roll = is_gm
    result.roll_source = body.roll_source

    await _publish_and_log(entry, member, user, result, db)
    await CombatService.apply_initiative_roll(
        db,
        session_id,
        body.actor_kind,
        body.actor_ref_id,
        result.total,
    )
    return result


@router.post("/sessions/{session_id}/rolls/attack-base", response_model=RollResult)
async def roll_attack_base(
    session_id: str,
    body: AttackBaseRollRequest,
    user: User = Depends(get_current_user),
    db: DbSession = Depends(get_session),
):
    entry, member = _get_session_and_member(session_id, user, db)
    is_gm = _authorize_roll(member, body.actor_kind, body.actor_ref_id, user.id)
    stats = _build_actor_stats(db, session_id, body.actor_kind, body.actor_ref_id)

    result = resolve_attack_base(
        stats, body.advantage_mode, body.bonus_override, body.target_ac,
        body.roll_source, body.manual_roll, body.manual_rolls,
    )
    result.is_gm_roll = is_gm
    result.roll_source = body.roll_source

    await _publish_and_log(entry, member, user, result, db)
    return result
