from fastapi import APIRouter, Depends
from pydantic import AliasChoices, BaseModel, Field
from sqlmodel import Session

from app.api.deps import get_current_user, get_session
from app.api.routes.combat import _is_session_gm, _publish_roll_result
from app.models.user import User
from app.schemas.combat import (
    CombatAreaPreviewRequest,
    CombatAreaPreviewResponse,
    CombatCastSpellRequest,
    CombatConditionEscapeRequest,
    CombatConditionWakeRequest,
    IllusionInvestigateRequest,
    IllusionUpdateRequest,
    IllusionRevealRequest,
    CombatMapPreviewState,
    CombatMovementPreviewRequest,
    CombatMovementPreviewResponse,
    CombatResolveSpellContextRequest,
    CombatResolvedSpellContext,
    CombatResolveSpellEffectRequest,
    CombatSpellResult,
)
from app.services.combat import CombatService


class SpiritualWeaponActionRequest(BaseModel):
    actor_participant_id: str
    anchor_id: str
    destination: dict | None = None
    target_ref_id: str | None = None
    target_kind: str | None = None
    manual_roll: int | None = None


class MageHandActionRequest(BaseModel):
    actor_participant_id: str
    anchor_id: str
    destination: dict


class CompelledDuelMovementSaveRequest(BaseModel):
    actor_participant_id: str | None = None
    manual_roll: int | None = None


class CrownOfMadnessForcedAttackRequest(BaseModel):
    controlled_target_ref_id: str
    forced_attack_target_ref_id: str | None = None
    weapon_item_id: str | None = None
    combat_action_id: str | None = None


class CrownOfMadnessMaintainRequest(BaseModel):
    actor_participant_id: str | None = None
    target_ref_id: str
    override_resource_limit: bool = False


class MaintainCastRequest(BaseModel):
    pending_cast_id: str = Field(
        validation_alias=AliasChoices("pending_cast_id", "pendingCastId"),
    )
    actor_participant_id: str | None = None
    override_resource_limit: bool = False


class HellishRebukeRequest(BaseModel):
    reaction_opportunity_id: str = Field(
        validation_alias=AliasChoices("reaction_opportunity_id", "reactionOpportunityId"),
    )
    slot_level: int = Field(
        validation_alias=AliasChoices("slot_level", "slotLevel"),
    )
    actor_participant_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("actor_participant_id", "actorParticipantId"),
    )
    override_resource_limit: bool = Field(
        default=False,
        validation_alias=AliasChoices("override_resource_limit", "overrideResourceLimit"),
    )


class MoonbeamTriggerEnterRequest(BaseModel):
    area_effect_id: str = Field(
        validation_alias=AliasChoices("area_effect_id", "areaEffectId"),
    )
    target_ref_id: str = Field(
        validation_alias=AliasChoices("target_ref_id", "targetRefId"),
    )
    actor_participant_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("actor_participant_id", "actorParticipantId"),
    )


class MoonbeamMoveRequest(BaseModel):
    area_effect_id: str = Field(
        validation_alias=AliasChoices("area_effect_id", "areaEffectId"),
    )
    new_point: dict = Field(
        validation_alias=AliasChoices("new_point", "newPoint"),
    )
    actor_participant_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("actor_participant_id", "actorParticipantId"),
    )
    override_resource_limit: bool = Field(
        default=False,
        validation_alias=AliasChoices("override_resource_limit", "overrideResourceLimit"),
    )


router = APIRouter()


@router.post(
    "/sessions/{session_id}/combat/action/cast", response_model=CombatSpellResult
)
async def action_cast_spell(
    session_id: str,
    req: CombatCastSpellRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    result = await CombatService.cast_spell(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    await _publish_roll_result(db, session_id, user, result.get("roll_result"))
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.get(
    "/sessions/{session_id}/combat/map-state",
    response_model=CombatMapPreviewState,
)
def get_area_targeting_map_state(
    session_id: str,
    actor_participant_id: str | None = None,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return CombatService.get_area_targeting_map_state(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        actor_participant_id=actor_participant_id,
    )


@router.post(
    "/sessions/{session_id}/combat/action/cast/preview",
    response_model=CombatAreaPreviewResponse,
)
def action_cast_spell_preview(
    session_id: str,
    req: CombatAreaPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return CombatService.preview_area_spell_targeting(
        db,
        session_id,
        req,
        user.id,
        _is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/spells/resolve-context",
    response_model=CombatResolvedSpellContext,
)
def resolve_spell_context(
    session_id: str,
    req: CombatResolveSpellContextRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return CombatService.resolve_spell_context(
        db,
        session_id,
        req,
        user.id,
        _is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/action/move/preview",
    response_model=CombatMovementPreviewResponse,
)
async def action_move_preview(
    session_id: str,
    req: CombatMovementPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.preview_movement(
        db,
        session_id,
        req,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/action/move",
    response_model=CombatMovementPreviewResponse,
)
async def action_move(
    session_id: str,
    req: CombatMovementPreviewRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.confirm_movement(
        db,
        session_id,
        req,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/spell/compelled-duel/movement-save",
)
async def action_compelled_duel_movement_save(
    session_id: str,
    req: CompelledDuelMovementSaveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_compelled_duel_movement_save(
        db,
        session_id,
        actor_participant_id=req.actor_participant_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        manual_roll=req.manual_roll,
    )


@router.post(
    "/sessions/{session_id}/combat/conditions/escape",
)
async def action_condition_escape(
    session_id: str,
    req: CombatConditionEscapeRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_condition_escape_action(
        db,
        session_id,
        actor_participant_id=req.actor_participant_id,
        target_participant_id=req.target_participant_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        condition_type=req.condition_type,
        source_effect_id=req.source_effect_id,
        roll_source=req.roll_source,
        manual_roll=req.manual_roll,
        manual_rolls=req.manual_rolls,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/conditions/wake",
)
async def action_condition_wake(
    session_id: str,
    req: CombatConditionWakeRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_condition_wake_action(
        db,
        session_id,
        actor_participant_id=req.actor_participant_id,
        target_ref_id=req.target_ref_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        source_effect_id=req.source_effect_id,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/illusions/investigate",
)
async def action_illusion_investigate(
    session_id: str,
    req: IllusionInvestigateRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_illusion_investigation(
        db,
        session_id,
        actor_participant_id=req.actor_participant_id,
        illusion_id=req.illusion_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        roll_source=req.roll_source,
        manual_roll=req.manual_roll,
        manual_rolls=req.manual_rolls,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/illusions/update",
)
async def action_illusion_update(
    session_id: str,
    req: IllusionUpdateRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_illusion_update(
        db,
        session_id,
        actor_participant_id=req.actor_participant_id,
        illusion_id=req.illusion_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        point=req.point.model_dump() if req.point is not None else None,
        appearance=req.appearance.model_dump() if req.appearance is not None else None,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/illusions/reveal-by-interaction",
)
async def action_illusion_reveal_by_interaction(
    session_id: str,
    req: IllusionRevealRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_illusion_reveal_by_interaction(
        db,
        session_id,
        actor_ref_id=req.actor_ref_id,
        illusion_id=req.illusion_id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post(
    "/sessions/{session_id}/combat/spell/crown-of-madness/forced-attack",
)
async def action_crown_of_madness_forced_attack(
    session_id: str,
    req: CrownOfMadnessForcedAttackRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_crown_of_madness_forced_attack(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        controlled_target_ref_id=req.controlled_target_ref_id,
        forced_attack_target_ref_id=req.forced_attack_target_ref_id,
        weapon_item_id=req.weapon_item_id,
        combat_action_id=req.combat_action_id,
    )


@router.post(
    "/sessions/{session_id}/combat/spell/crown-of-madness/maintain",
)
async def action_crown_of_madness_maintain(
    session_id: str,
    req: CrownOfMadnessMaintainRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_crown_of_madness_maintain(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        actor_participant_id=req.actor_participant_id,
        target_ref_id=req.target_ref_id,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/spells/maintain-cast",
)
async def action_maintain_pending_spell_cast(
    session_id: str,
    req: MaintainCastRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.resolve_pending_spell_cast_maintain(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        actor_participant_id=req.actor_participant_id,
        pending_cast_id=req.pending_cast_id,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/spells/hellish-rebuke",
)
async def action_hellish_rebuke(
    session_id: str,
    req: HellishRebukeRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None
    return await CombatService.resolve_hellish_rebuke_reaction(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        reaction_opportunity_id=req.reaction_opportunity_id,
        slot_level=req.slot_level,
        actor_participant_id=req.actor_participant_id,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/spells/moonbeam/trigger-enter",
)
async def action_moonbeam_trigger_enter(
    session_id: str,
    req: MoonbeamTriggerEnterRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None
    return await CombatService.resolve_moonbeam_enter_trigger(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        area_effect_id=req.area_effect_id,
        target_ref_id=req.target_ref_id,
        actor_participant_id=req.actor_participant_id,
    )


@router.post(
    "/sessions/{session_id}/combat/spells/moonbeam/move",
)
async def action_moonbeam_move(
    session_id: str,
    req: MoonbeamMoveRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None
    return await CombatService.resolve_moonbeam_move(
        db,
        session_id,
        actor_user_id=user.id,
        is_gm=_is_session_gm(db, session_id, user),
        area_effect_id=req.area_effect_id,
        new_point=req.new_point,
        actor_participant_id=req.actor_participant_id,
        override_resource_limit=req.override_resource_limit,
    )


@router.post(
    "/sessions/{session_id}/combat/action/cast/effect", response_model=CombatSpellResult
)
async def action_cast_spell_effect(
    session_id: str,
    req: CombatResolveSpellEffectRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    result = await CombatService.cast_spell_effect(
        db, session_id, req, user.id, _is_session_gm(db, session_id, user)
    )
    concentration_roll = (
        result.get("concentration_check", {}).get("roll_result")
        if isinstance(result.get("concentration_check"), dict)
        else None
    )
    await _publish_roll_result(db, session_id, user, concentration_roll)
    return result


@router.post("/sessions/{session_id}/combat/spiritual-weapon-action")
async def spiritual_weapon_action(
    session_id: str,
    req: SpiritualWeaponActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.use_spiritual_weapon_action(
        db,
        session_id,
        req,
        user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )


@router.post("/sessions/{session_id}/combat/mage-hand-action")
async def mage_hand_action(
    session_id: str,
    req: MageHandActionRequest,
    db: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    assert user.id is not None  # authenticated user always has an id
    return await CombatService.use_mage_hand_action(
        db,
        session_id,
        req,
        user.id,
        is_gm=_is_session_gm(db, session_id, user),
    )
