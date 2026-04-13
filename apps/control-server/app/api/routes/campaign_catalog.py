from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_campaign_member, require_gm
from app.api.serializers.item import to_item_read
from app.db.session import get_session
from app.models.base_item import BaseItemKind
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.item import ItemRead
from app.services.campaign_catalog import list_campaign_catalog, snapshot_campaign_catalog

router = APIRouter()


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
    if campaign.item_catalog_snapshot_at is not None:
        raise HTTPException(
            status_code=409,
            detail="Campaign item catalog snapshot is locked after campaign creation",
        )
    result = snapshot_campaign_catalog(campaign=campaign, db=session)
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
