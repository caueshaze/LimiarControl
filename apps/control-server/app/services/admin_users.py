from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import case, delete, func, or_, update
from sqlmodel import Session, select

from app.models.base_item import BaseItem
from app.models.base_spell import BaseSpell
from app.models.campaign import Campaign, RoleMode
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
from app.models.session_state import SessionState
from app.models.user import User
from app.schemas.admin_system import (
    AdminOverviewRead,
    AdminUserRead,
    AdminUserUpdate,
)
from app.services.campaign_cleanup import delete_campaign_tree, delete_party_tree
from app.services.media_storage_service import delete_campaign_prefix_best_effort


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

    deleted_campaign_ids: list[str] = []
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
            deleted_campaign_ids.append(campaign_id)

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
    for campaign_id in deleted_campaign_ids:
        delete_campaign_prefix_best_effort(campaign_id)
