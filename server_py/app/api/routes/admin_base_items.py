from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.api.deps import require_system_admin
from app.api.serializers.base_item import to_base_item_read
from app.db.session import get_session
from app.models.base_item import BaseItemEquipmentCategory, BaseItemKind
from app.models.campaign import SystemType
from app.models.user import User
from app.schemas.base_item import BaseItemCreate, BaseItemRead, BaseItemUpdate
from app.services.base_item_seeds import import_base_item_seed_file
from app.services.base_items import (
    create_base_item,
    delete_base_item,
    get_base_item_by_id,
    list_base_items,
    update_base_item,
)

router = APIRouter()


class BaseItemSeedSyncResult(BaseModel):
    inserted: int
    updated: int
    total: int


@router.get("/base-items", response_model=list[BaseItemRead])
def admin_list_base_items(
    system: SystemType | None = None,
    item_kind: BaseItemKind | None = None,
    canonical_key: str | None = None,
    search: str | None = None,
    equipment_category: BaseItemEquipmentCategory | None = None,
    is_active: bool | None = None,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    items = list_base_items(
        db=session,
        system=system,
        item_kind=item_kind,
        canonical_key=canonical_key,
        search=search,
        equipment_category=equipment_category,
        is_active=is_active,
    )
    return [to_base_item_read(item) for item in items]


@router.post("/base-items/sync-seed", response_model=BaseItemSeedSyncResult)
def admin_sync_base_items_seed(
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    result = import_base_item_seed_file(session, replace=False)
    return BaseItemSeedSyncResult(**result)


@router.get("/base-items/{base_item_id}", response_model=BaseItemRead)
def admin_get_base_item(
    base_item_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    item = get_base_item_by_id(db=session, base_item_id=base_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Base item not found")
    return to_base_item_read(item)


@router.post("/base-items", response_model=BaseItemRead, status_code=201)
def admin_create_base_item(
    payload: BaseItemCreate,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    item = create_base_item(db=session, payload=payload)
    return to_base_item_read(item)


@router.put("/base-items/{base_item_id}", response_model=BaseItemRead)
def admin_update_base_item(
    base_item_id: str,
    payload: BaseItemUpdate,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    item = get_base_item_by_id(db=session, base_item_id=base_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Base item not found")
    updated = update_base_item(db=session, item=item, payload=payload)
    return to_base_item_read(updated)


@router.delete("/base-items/{base_item_id}", status_code=204)
def admin_delete_base_item(
    base_item_id: str,
    _user: User = Depends(require_system_admin),
    session: Session = Depends(get_session),
):
    item = get_base_item_by_id(db=session, base_item_id=base_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Base item not found")
    delete_base_item(db=session, item=item)
    return None
