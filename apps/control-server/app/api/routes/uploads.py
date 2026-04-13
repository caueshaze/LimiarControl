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
)

router = APIRouter()

CHUNK_SIZE = 64 * 1024  # 64 KB
UPLOAD_KINDS = {"campaign_map", "campaign_entity"}


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
    campaignId: str = Form(...),
    entityId: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if kind not in UPLOAD_KINDS:
        raise HTTPException(status_code=400, detail="Invalid upload kind.")
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

    try:
        if kind == "campaign_map":
            url = upload_map_image(contents, file.content_type or "", campaignId)
        else:
            url = upload_entity_image(contents, file.content_type or "", campaignId)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Falha ao fazer upload da imagem.") from exc

    return {"url": url}
