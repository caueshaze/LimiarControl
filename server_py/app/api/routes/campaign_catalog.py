from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.db.session import get_session
from app.models.base_item import BaseItemKind
from app.models.campaign import Campaign
from app.models.item import Item
from app.models.user import User
from app.schemas.item import ItemRead
from app.services.campaign_catalog import list_campaign_catalog, seed_campaign_catalog

router = APIRouter()


def to_item_read(item: Item) -> ItemRead:
    return ItemRead(
        id=item.id,
        campaignId=item.campaign_id,
        name=item.name,
        type=item.type,
        description=item.description,
        price=item.price,
        weight=item.weight,
        damageDice=item.damage_dice,
        rangeMeters=item.range_meters,
        properties=item.properties,
        baseItemId=item.base_item_id,
        canonicalKeySnapshot=item.canonical_key_snapshot,
        nameEnSnapshot=item.name_en_snapshot,
        namePtSnapshot=item.name_pt_snapshot,
        itemKind=item.item_kind,
        costUnit=item.cost_unit,
        isCustom=item.is_custom,
        isEnabled=item.is_enabled,
        createdAt=item.created_at,
        updatedAt=item.updated_at,
    )


class CatalogSeedResult(BaseModel):
    inserted: int
    existing: int


@router.post(
    "/{campaign_id}/catalog/seed",
    response_model=CatalogSeedResult,
)
def seed_catalog(
    campaign_id: str,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """Materialize base items into campaign catalog. Idempotent."""
    require_gm(campaign_id, user, session)
    campaign = session.exec(select(Campaign).where(Campaign.id == campaign_id)).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    result = seed_campaign_catalog(campaign_id, campaign.system, session)
    return CatalogSeedResult(**result)


@router.get(
    "/{campaign_id}/catalog",
    response_model=list[ItemRead],
)
def list_catalog(
    campaign_id: str,
    item_kind: Optional[BaseItemKind] = Query(default=None),
    search: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """List campaign catalog items with optional filters."""
    require_campaign_member(campaign_id, user, session)
    items = list_campaign_catalog(
        campaign_id,
        session,
        item_kind=item_kind,
        search=search,
    )
    return [to_item_read(item) for item in items]
