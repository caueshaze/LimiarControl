from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.deps import get_current_user
from app.api.serializers.base_item import to_base_item_read
from app.db.session import get_session
from app.models.base_item import BaseItemKind
from app.models.campaign import SystemType
from app.models.user import User
from app.schemas.base_item import BaseItemRead
from app.services.base_items import (
    get_base_item_by_id,
    list_base_items as list_catalog_base_items,
)

router = APIRouter()


@router.get("", response_model=list[BaseItemRead])
def list_base_items(
    system: SystemType | None = None,
    item_kind: BaseItemKind | None = None,
    canonical_key: str | None = None,
    search: str | None = None,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    items = list_catalog_base_items(
        db=session,
        system=system,
        item_kind=item_kind,
        canonical_key=canonical_key,
        search=search,
    )
    return [to_base_item_read(item) for item in items]


@router.get("/{base_item_id}", response_model=BaseItemRead)
def get_base_item(
    base_item_id: str,
    _user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    item = get_base_item_by_id(db=session, base_item_id=base_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Base item not found")

    return to_base_item_read(item)
