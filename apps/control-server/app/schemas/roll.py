from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.campaign_entity_shared import AbilityName, SkillName

AdvantageMode = Literal["normal", "advantage", "disadvantage"]
ActorKind = Literal["player", "session_entity"]
RollType = Literal["ability", "save", "skill", "initiative", "attack"]
RollSource = Literal["system", "manual"]


# ---------------------------------------------------------------------------
# Request schemas (one per endpoint)
# ---------------------------------------------------------------------------

class _RollRequestBase(BaseModel):
    actor_kind: ActorKind
    actor_ref_id: str
    advantage_mode: AdvantageMode = "normal"
    bonus_override: int | None = None
    roll_source: RollSource = "system"
    manual_roll: int | None = Field(default=None, ge=1, le=20)
    manual_rolls: list[int] | None = None  # 2 d20 values for adv/disadv manual


class AbilityRollRequest(_RollRequestBase):
    ability: AbilityName
    dc: int | None = Field(default=None, ge=1)


class SaveRollRequest(_RollRequestBase):
    ability: AbilityName
    dc: int | None = Field(default=None, ge=1)


class SkillRollRequest(_RollRequestBase):
    skill: SkillName
    dc: int | None = Field(default=None, ge=1)


class InitiativeRollRequest(_RollRequestBase):
    pass


class AttackBaseRollRequest(_RollRequestBase):
    target_ac: int | None = Field(default=None, ge=0)


# ---------------------------------------------------------------------------
# Internal stat container (not exposed via API)
# ---------------------------------------------------------------------------

class RollActorStats(BaseModel):
    display_name: str
    abilities: dict[str, int]
    saving_throws: dict[str, int] | None = None
    skills: dict[str, int] | None = None
    initiative_bonus: int | None = None
    proficiency_bonus: int = 2
    actor_kind: ActorKind
    actor_ref_id: str


# ---------------------------------------------------------------------------
# Result schema (unified for all roll types)
# ---------------------------------------------------------------------------

class RollResult(BaseModel):
    event_id: str
    roll_type: RollType
    actor_kind: ActorKind
    actor_ref_id: str
    actor_display_name: str

    # D20 results
    rolls: list[int]  # always 2 values (both d20s)
    selected_roll: int  # the d20 value used after advantage/disadvantage
    advantage_mode: AdvantageMode

    # Modifier
    modifier_used: int
    override_used: bool
    formula: str  # e.g. "1d20 + 3"
    total: int  # selected_roll + modifier_used

    # Context-dependent
    ability: AbilityName | None = None
    skill: SkillName | None = None
    dc: int | None = None
    target_ac: int | None = None
    success: bool | None = None  # None if no dc/target_ac provided

    is_gm_roll: bool = False
    roll_source: RollSource = "system"
    timestamp: datetime
