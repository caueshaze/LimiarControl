from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.base_spell import SpellSchool
from app.models.campaign import SystemType

from .base_spell_upcast import SpellUpcastConfig


class BaseSpellAliasRead(BaseModel):
    id: str
    alias: str
    locale: Optional[str] = None
    aliasType: Optional[str] = None


class BaseSpellRead(BaseModel):
    id: str
    system: SystemType
    canonicalKey: str
    nameEn: str
    namePt: Optional[str] = None
    descriptionEn: str
    descriptionPt: Optional[str] = None
    level: int
    school: SpellSchool
    classesJson: Optional[Any] = None

    castingTimeType: Optional[str] = None
    castingTime: Optional[str] = None
    rangeMeters: Optional[int] = None
    rangeText: Optional[str] = None
    targetType: Optional[str] = None
    selectionType: Optional[str] = None
    originType: Optional[str] = None
    targetAnchor: Optional[str] = None
    attackType: Optional[str] = None
    rangeKind: Optional[str] = None
    effectTiming: Optional[str] = None
    areaShape: Optional[str] = None
    radiusMeters: Optional[float] = None
    lengthMeters: Optional[float] = None
    sideMeters: Optional[float] = None
    duration: Optional[str] = None
    componentsJson: Optional[Any] = None
    materialComponentText: Optional[str] = None
    concentration: bool
    ritual: bool

    resolutionType: Optional[str] = None
    savingThrow: Optional[str] = None
    saveSuccessOutcome: Optional[str] = None
    coverAppliesToSave: Optional[str] = None

    damageDice: Optional[str] = None
    damageType: Optional[str] = None
    healDice: Optional[str] = None

    requiresTargetSight: Optional[bool] = None
    requiresTargetEffect: Optional[bool] = None
    requiresPointSight: Optional[bool] = None
    requiresPointEffect: Optional[bool] = None

    upcast: Optional[SpellUpcastConfig] = None
    upcastMode: Optional[str] = None
    upcastValue: Optional[str] = None

    automationMode: Optional[str] = None
    defaultSpellMode: Optional[str] = None
    requiresEffectInputs: Optional[bool] = None
    requiresMap: Optional[bool] = None
    handlerKey: Optional[str] = None

    source: Optional[str] = None
    sourceRef: Optional[str] = None
    isSrd: bool
    isActive: bool
    aliases: list[BaseSpellAliasRead] = Field(default_factory=list)
