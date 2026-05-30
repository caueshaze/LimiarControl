from typing import cast

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from app.api.deps import get_current_user, require_gm
from app.db.session import get_session
from app.models.campaign_entity import CampaignEntity
from app.models.user import User
from app.services.media_storage_service import (
    MAX_FILE_SIZE_BYTES,
    upload_entity_image,
    upload_map_image,
    upload_user_avatar,
    upload_user_token,
)

router = APIRouter()

CHUNK_SIZE = 64 * 1024  # 64 KB
UPLOAD_KINDS = {"campaign_map", "campaign_entity", "user_avatar", "user_token"}
USER_UPLOAD_KINDS = {"user_avatar", "user_token"}


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Read upload in chunks, abort early if size exceeds limit."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    kind: str = Form(...),
    campaignId: str | None = Form(default=None),
    entityId: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if kind not in UPLOAD_KINDS:
        raise HTTPException(status_code=400, detail="Invalid upload kind.")

    is_user_upload = kind in USER_UPLOAD_KINDS

    if is_user_upload:
        if entityId is not None:
            raise HTTPException(
                status_code=400,
                detail="entityId is not allowed for user uploads.",
            )
    else:
        if not campaignId:
            raise HTTPException(status_code=400, detail="campaignId is required.")
        require_gm(campaignId, current_user, session)
        if kind != "campaign_entity" and entityId is not None:
            raise HTTPException(
                status_code=400,
                detail="entityId is only allowed for campaign_entity uploads.",
            )
        if entityId is not None:
            entry = session.exec(
                select(CampaignEntity).where(
                    CampaignEntity.id == entityId,
                    CampaignEntity.campaign_id == campaignId,
                )
            ).first()
            if not entry:
                raise HTTPException(status_code=404, detail="Entity not found")

    contents = await _read_limited(file, MAX_FILE_SIZE_BYTES)
    assert current_user.id is not None  # authenticated user always has an id

    try:
        if kind == "campaign_map":
            # campaignId is validated non-None above for non-user uploads.
            url = upload_map_image(contents, file.content_type or "", cast(str, campaignId))
        elif kind == "campaign_entity":
            url = upload_entity_image(contents, file.content_type or "", cast(str, campaignId))
        elif kind == "user_avatar":
            url = upload_user_avatar(contents, file.content_type or "", current_user.id)
        elif kind == "user_token":
            url = upload_user_token(contents, file.content_type or "", current_user.id)
        else:  # unreachable due to validation above
            raise HTTPException(status_code=400, detail="Invalid upload kind.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Falha ao fazer upload da imagem.") from exc

    return {"url": url}
