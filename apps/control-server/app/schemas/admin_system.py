from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.campaign import RoleMode, SystemType


class AdminOverviewRead(BaseModel):
    usersTotal: int
    systemAdminsTotal: int
    campaignsTotal: int
    partiesTotal: int
    sessionsTotal: int
    activeSessionsTotal: int
    baseItemsActive: int
    baseItemsInactive: int
    baseSpellsActive: int
    baseSpellsInactive: int


class AdminUserRead(BaseModel):
    id: str
    username: str
    displayName: str
    role: RoleMode
    isSystemAdmin: bool
    campaignsCount: int
    gmCampaignsCount: int
    partiesCount: int
    createdAt: datetime
    updatedAt: datetime | None = None


class AdminUserUpdate(BaseModel):
    role: RoleMode | None = None
    isSystemAdmin: bool | None = None


class AdminCampaignRead(BaseModel):
    id: str
    name: str
    systemType: SystemType
    roleMode: RoleMode
    gmNames: list[str]
    membersCount: int
    partiesCount: int
    sessionsCount: int
    activeSessionsCount: int
    itemCatalogSnapshotAt: datetime | None = None
    spellCatalogSnapshotAt: datetime | None = None
    createdAt: datetime
    updatedAt: datetime | None = None


class AdminDiagnosticsRead(BaseModel):
    appEnv: str
    autoMigrate: bool
    utcNow: datetime
    databaseOk: bool
    databaseMessage: str | None = None
    usersTotal: int
    campaignsTotal: int
    partiesTotal: int
    sessionsTotal: int
    activeSessionsTotal: int
    activeCombatsTotal: int
