from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import case, delete, func, or_, update
from sqlmodel import Session, select

from app.core.config import settings
from app.models.base_item import BaseItem
from app.models.base_spell import BaseSpell
from app.models.campaign import Campaign, RoleMode, SystemType
from app.models.campaign_member import CampaignMember
from app.models.character_sheet import CharacterSheet
from app.models.inventory import InventoryItem
from app.models.party import Party
from app.models.party_character_sheet_draft import PartyCharacterSheetDraft
from app.models.party_member import PartyMember
from app.models.preferences import Preferences
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session as CampaignSession, SessionStatus
from app.models.session_command_event import SessionCommandEvent
from app.models.session_runtime import SessionRuntime
from app.models.session_state import SessionState
from app.models.user import User
from app.schemas.admin_system import (
    AdminCampaignRead,
    AdminDiagnosticsRead,
    AdminOverviewRead,
    AdminUserRead,
    AdminUserUpdate,
)
from app.services.campaign_cleanup import delete_campaign_tree, delete_party_tree


def _count_rows(db: Session, model, *clauses) -> int:
    statement = select(func.count()).select_from(model)
    for clause in clauses:
        statement = statement.where(clause)
    return db.exec(statement).one()


def get_admin_overview(*, db: Session) -> AdminOverviewRead:
    return AdminOverviewRead(
        usersTotal=_count_rows(db, User),
        systemAdminsTotal=_count_rows(db, User, User.is_system_admin == True),  # noqa: E712
        campaignsTotal=_count_rows(db, Campaign),
        partiesTotal=_count_rows(db, Party),
        sessionsTotal=_count_rows(db, CampaignSession),
        activeSessionsTotal=_count_rows(
            db,
            CampaignSession,
            CampaignSession.status == SessionStatus.ACTIVE,
        ),
        baseItemsActive=_count_rows(db, BaseItem, BaseItem.is_active == True),  # noqa: E712
        baseItemsInactive=_count_rows(db, BaseItem, BaseItem.is_active == False),  # noqa: E712
        baseSpellsActive=_count_rows(db, BaseSpell, BaseSpell.is_active == True),  # noqa: E712
        baseSpellsInactive=_count_rows(db, BaseSpell, BaseSpell.is_active == False),  # noqa: E712
    )


def list_admin_users(
    *,
    db: Session,
    search: str | None = None,
    role: RoleMode | None = None,
    is_system_admin: bool | None = None,
    limit: int = 100,
) -> list[AdminUserRead]:
    statement = (
        select(
            User.id,
            User.username,
            User.display_name,
            User.role,
            User.is_system_admin,
            User.created_at,
            User.updated_at,
            func.count(func.distinct(CampaignMember.campaign_id)).label("campaigns_count"),
            func.count(
                func.distinct(
                    case(
                        (CampaignMember.role_mode == RoleMode.GM, CampaignMember.campaign_id),
                    )
                )
            ).label("gm_campaigns_count"),
            func.count(func.distinct(PartyMember.party_id)).label("parties_count"),
        )
        .select_from(User)
        .outerjoin(CampaignMember, CampaignMember.user_id == User.id)
        .outerjoin(PartyMember, PartyMember.user_id == User.id)
        .group_by(
            User.id,
            User.username,
            User.display_name,
            User.role,
            User.is_system_admin,
            User.created_at,
            User.updated_at,
        )
        .order_by(User.created_at.desc())
        .limit(limit)
    )

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                User.username.ilike(pattern),
                User.display_name.ilike(pattern),
            )
        )
    if role is not None:
        statement = statement.where(User.role == role)
    if is_system_admin is not None:
        statement = statement.where(User.is_system_admin == is_system_admin)  # noqa: E712

    rows = db.exec(statement).all()
    return [
        AdminUserRead(
            id=user_id,
            username=username,
            displayName=display_name or username,
            role=user_role,
            isSystemAdmin=user_is_system_admin,
            campaignsCount=campaigns_count,
            gmCampaignsCount=gm_campaigns_count,
            partiesCount=parties_count,
            createdAt=created_at,
            updatedAt=updated_at,
        )
        for (
            user_id,
            username,
            display_name,
            user_role,
            user_is_system_admin,
            created_at,
            updated_at,
            campaigns_count,
            gm_campaigns_count,
            parties_count,
        ) in rows
    ]


def get_admin_user_by_id(*, db: Session, user_id: str) -> User | None:
    return db.exec(select(User).where(User.id == user_id)).first()


def update_admin_user(*, db: Session, user_id: str, payload: AdminUserUpdate) -> AdminUserRead:
    user = get_admin_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if payload.role is None and payload.isSystemAdmin is None:
        raise HTTPException(status_code=400, detail="No admin fields provided")

    if payload.role is not None:
        user.role = payload.role
    if payload.isSystemAdmin is not None:
        user.is_system_admin = payload.isSystemAdmin

    db.add(user)
    db.commit()
    db.refresh(user)

    campaigns_count = db.exec(
        select(func.count(func.distinct(CampaignMember.campaign_id))).where(
            CampaignMember.user_id == user.id,
        )
    ).one()
    gm_campaigns_count = db.exec(
        select(func.count(func.distinct(CampaignMember.campaign_id))).where(
            CampaignMember.user_id == user.id,
            CampaignMember.role_mode == RoleMode.GM,
        )
    ).one()
    parties_count = db.exec(
        select(func.count(func.distinct(PartyMember.party_id))).where(
            PartyMember.user_id == user.id,
        )
    ).one()

    return AdminUserRead(
        id=user.id,
        username=user.username,
        displayName=user.display_name or user.username,
        role=user.role,
        isSystemAdmin=user.is_system_admin,
        campaignsCount=campaigns_count,
        gmCampaignsCount=gm_campaigns_count,
        partiesCount=parties_count,
        createdAt=user.created_at,
        updatedAt=user.updated_at,
    )


def delete_admin_user(*, db: Session, user_id: str) -> None:
    user = get_admin_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    gm_campaign_ids = [
        campaign_id
        for campaign_id in db.exec(
            select(CampaignMember.campaign_id).where(
                CampaignMember.user_id == user_id,
                CampaignMember.role_mode == RoleMode.GM,
            )
        ).all()
        if campaign_id
    ]

    for campaign_id in gm_campaign_ids:
        other_gm_exists = db.exec(
            select(CampaignMember.id)
            .where(
                CampaignMember.campaign_id == campaign_id,
                CampaignMember.role_mode == RoleMode.GM,
                CampaignMember.user_id != user_id,
            )
            .limit(1)
        ).first()
        if other_gm_exists is not None:
            continue

        campaign = db.get(Campaign, campaign_id)
        if campaign is not None:
            delete_campaign_tree(db, campaign)

    remaining_gm_parties = db.exec(select(Party).where(Party.gm_user_id == user_id)).all()
    for party in remaining_gm_parties:
        delete_party_tree(db, party)

    remaining_member_ids = [
        member_id
        for member_id in db.exec(
            select(CampaignMember.id).where(CampaignMember.user_id == user_id)
        ).all()
        if member_id
    ]

    if remaining_member_ids:
        db.exec(delete(InventoryItem).where(InventoryItem.member_id.in_(remaining_member_ids)))
        db.exec(delete(PurchaseEvent).where(PurchaseEvent.member_id.in_(remaining_member_ids)))
        db.exec(
            delete(SessionCommandEvent).where(
                SessionCommandEvent.member_id.in_(remaining_member_ids)
            )
        )

    db.exec(
        update(CharacterSheet)
        .where(CharacterSheet.delivered_by_user_id == user_id)
        .values(delivered_by_user_id=None)
    )
    db.exec(update(PurchaseEvent).where(PurchaseEvent.user_id == user_id).values(user_id=None))
    db.exec(
        update(SessionCommandEvent)
        .where(SessionCommandEvent.user_id == user_id)
        .values(user_id=None)
    )
    db.exec(update(RollEvent).where(RollEvent.user_id == user_id).values(user_id=None))

    db.exec(delete(SessionState).where(SessionState.player_user_id == user_id))
    db.exec(delete(CharacterSheet).where(CharacterSheet.player_user_id == user_id))
    db.exec(
        delete(PartyCharacterSheetDraft).where(
            PartyCharacterSheetDraft.created_by_user_id == user_id
        )
    )
    db.exec(delete(PartyMember).where(PartyMember.user_id == user_id))
    db.exec(delete(Preferences).where(Preferences.user_id == user_id))
    db.exec(delete(CampaignMember).where(CampaignMember.user_id == user_id))
    db.delete(user)
    db.commit()


def list_admin_campaigns(
    *,
    db: Session,
    search: str | None = None,
    system: SystemType | None = None,
    limit: int = 100,
) -> list[AdminCampaignRead]:
    statement = (
        select(
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.role_mode,
            Campaign.item_catalog_snapshot_at,
            Campaign.spell_catalog_snapshot_at,
            Campaign.created_at,
            Campaign.updated_at,
            func.count(func.distinct(CampaignMember.user_id)).label("members_count"),
            func.count(func.distinct(Party.id)).label("parties_count"),
            func.count(func.distinct(CampaignSession.id)).label("sessions_count"),
            func.count(
                func.distinct(
                    case(
                        (CampaignSession.status == SessionStatus.ACTIVE, CampaignSession.id),
                    )
                )
            ).label("active_sessions_count"),
        )
        .select_from(Campaign)
        .outerjoin(CampaignMember, CampaignMember.campaign_id == Campaign.id)
        .outerjoin(Party, Party.campaign_id == Campaign.id)
        .outerjoin(CampaignSession, CampaignSession.campaign_id == Campaign.id)
        .group_by(
            Campaign.id,
            Campaign.name,
            Campaign.system,
            Campaign.role_mode,
            Campaign.item_catalog_snapshot_at,
            Campaign.spell_catalog_snapshot_at,
            Campaign.created_at,
            Campaign.updated_at,
        )
        .order_by(Campaign.created_at.desc())
        .limit(limit)
    )

    if search and search.strip():
        statement = statement.where(Campaign.name.ilike(f"%{search.strip()}%"))
    if system is not None:
        statement = statement.where(Campaign.system == system)

    rows = db.exec(statement).all()
    campaign_ids = [campaign_id for campaign_id, *_rest in rows]

    gm_names_by_campaign: dict[str, list[str]] = defaultdict(list)
    if campaign_ids:
        gm_rows = db.exec(
            select(CampaignMember.campaign_id, CampaignMember.display_name)
            .where(
                CampaignMember.campaign_id.in_(campaign_ids),
                CampaignMember.role_mode == RoleMode.GM,
            )
            .order_by(CampaignMember.created_at)
        ).all()
        for campaign_id, display_name in gm_rows:
            if display_name not in gm_names_by_campaign[campaign_id]:
                gm_names_by_campaign[campaign_id].append(display_name)

    return [
        AdminCampaignRead(
            id=campaign_id,
            name=name,
            systemType=campaign_system,
            roleMode=role_mode,
            gmNames=gm_names_by_campaign.get(campaign_id, []),
            membersCount=members_count,
            partiesCount=parties_count,
            sessionsCount=sessions_count,
            activeSessionsCount=active_sessions_count,
            itemCatalogSnapshotAt=item_catalog_snapshot_at,
            spellCatalogSnapshotAt=spell_catalog_snapshot_at,
            createdAt=created_at,
            updatedAt=updated_at,
        )
        for (
            campaign_id,
            name,
            campaign_system,
            role_mode,
            item_catalog_snapshot_at,
            spell_catalog_snapshot_at,
            created_at,
            updated_at,
            members_count,
            parties_count,
            sessions_count,
            active_sessions_count,
        ) in rows
    ]


def delete_admin_campaign(*, db: Session, campaign_id: str) -> None:
    campaign = db.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    delete_campaign_tree(db, campaign)
    db.commit()


def get_admin_diagnostics(*, db: Session) -> AdminDiagnosticsRead:
    database_ok = True
    database_message = "ok"

    try:
        db.exec(select(1)).one()
    except Exception as exc:  # pragma: no cover - defensive branch
        database_ok = False
        database_message = str(exc)

    users_total = campaigns_total = parties_total = sessions_total = 0
    active_sessions_total = active_combats_total = 0

    try:
        users_total = _count_rows(db, User)
        campaigns_total = _count_rows(db, Campaign)
        parties_total = _count_rows(db, Party)
        sessions_total = _count_rows(db, CampaignSession)
        active_sessions_total = _count_rows(
            db,
            CampaignSession,
            CampaignSession.status == SessionStatus.ACTIVE,
        )
        active_combats_total = _count_rows(
            db,
            SessionRuntime,
            SessionRuntime.combat_active == True,  # noqa: E712
        )
    except Exception as exc:  # pragma: no cover - defensive branch
        database_ok = False
        database_message = str(exc)

    return AdminDiagnosticsRead(
        appEnv=settings.app_env,
        autoMigrate=settings.auto_migrate,
        utcNow=datetime.now(timezone.utc),
        databaseOk=database_ok,
        databaseMessage=database_message,
        usersTotal=users_total,
        campaignsTotal=campaigns_total,
        partiesTotal=parties_total,
        sessionsTotal=sessions_total,
        activeSessionsTotal=active_sessions_total,
        activeCombatsTotal=active_combats_total,
    )
