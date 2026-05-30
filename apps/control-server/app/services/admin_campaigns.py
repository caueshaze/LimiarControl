from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlmodel import Session, col, select

from app.models.campaign import Campaign, RoleMode, SystemType
from app.models.campaign_member import CampaignMember
from app.models.party import Party
from app.models.session import Session as CampaignSession, SessionStatus
from app.schemas.admin_system import AdminCampaignRead
from app.services.campaign_cleanup import delete_campaign_tree
from app.services.media_storage_service import delete_campaign_prefix_best_effort


def list_admin_campaigns(
    *,
    db: Session,
    search: str | None = None,
    system: SystemType | None = None,
    limit: int = 100,
) -> list[AdminCampaignRead]:
    statement = (
        select(  # type: ignore[call-overload]  # sqlmodel select() typed overloads cap at 4 columns
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
                        (col(CampaignSession.status) == SessionStatus.ACTIVE, CampaignSession.id),
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
        .order_by(col(Campaign.created_at).desc())
        .limit(limit)
    )

    if search and search.strip():
        statement = statement.where(col(Campaign.name).ilike(f"%{search.strip()}%"))
    if system is not None:
        statement = statement.where(Campaign.system == system)

    rows = db.exec(statement).all()
    campaign_ids = [campaign_id for campaign_id, *_rest in rows]

    gm_names_by_campaign: dict[str, list[str]] = defaultdict(list)
    if campaign_ids:
        gm_rows = db.exec(
            select(CampaignMember.campaign_id, CampaignMember.display_name)
            .where(
                col(CampaignMember.campaign_id).in_(campaign_ids),
                CampaignMember.role_mode == RoleMode.GM,
            )
            .order_by(col(CampaignMember.created_at))
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
    delete_campaign_prefix_best_effort(campaign_id)
