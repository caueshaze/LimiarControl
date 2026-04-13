from __future__ import annotations

import argparse
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import engine
from app.models.campaign_entity import CampaignEntity
from app.models.campaign_tactical_map import CampaignTacticalMap
from app.services.media_storage_service import (
    MAX_FILE_SIZE_BYTES,
    build_entity_asset_ref,
    copy_object,
    delete_managed_url_best_effort,
    is_managed_url,
    upload_entity_image,
    upload_map_image,
)


@dataclass
class MigrationFailure:
    record_type: str
    record_id: str
    source_url: str
    reason: str


def _allowed_origins() -> set[str]:
    return {origin.lower() for origin in settings.media_legacy_allowed_origins}


def _download_legacy_image(client: httpx.Client, url: str) -> tuple[bytes, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Legacy URL must use http or https")
    if parsed.netloc.lower() not in _allowed_origins():
        raise ValueError("Legacy URL origin is not allowed")

    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        final_host = response.url.host or ""
        if final_host.lower() not in _allowed_origins():
            raise ValueError("Legacy redirect target is not allowed")
        content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if not content_type.startswith("image/"):
            raise ValueError("Legacy response is not an image")
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > MAX_FILE_SIZE_BYTES:
                raise ValueError("Legacy image exceeds the maximum allowed size")
            chunks.append(chunk)
        return b"".join(chunks), content_type


def _migrate_campaign_map(
    client: httpx.Client,
    db: Session,
    map_config: CampaignTacticalMap,
) -> bool:
    if not map_config.image_url or is_managed_url(map_config.image_url):
        return False
    payload, content_type = _download_legacy_image(client, map_config.image_url)
    next_url = upload_map_image(payload, content_type, map_config.campaign_id)
    try:
        map_config.image_url = next_url
        db.add(map_config)
        db.commit()
    except Exception:
        delete_managed_url_best_effort(next_url)
        raise
    return True


def _migrate_campaign_entity(client: httpx.Client, db: Session, entity: CampaignEntity) -> bool:
    if not entity.image_url or is_managed_url(entity.image_url):
        return False
    payload, content_type = _download_legacy_image(client, entity.image_url)
    temporary_url = upload_entity_image(payload, content_type, entity.campaign_id)
    temporary_ref = None
    final_url = None
    try:
        from app.services.media_storage_service import parse_managed_url

        temporary_ref = parse_managed_url(temporary_url)
        final_ref = build_entity_asset_ref(entity.campaign_id, entity.id, temporary_ref.asset_id)
        copy_object(temporary_ref, final_ref)
        final_url = final_ref.url
        entity.image_url = final_url
        db.add(entity)
        db.commit()
        delete_managed_url_best_effort(temporary_url)
    except Exception:
        if final_url is not None:
            delete_managed_url_best_effort(final_url)
        raise
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill legacy media URLs into MinIO")
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="HTTP timeout when downloading legacy assets",
    )
    args = parser.parse_args()

    if not _allowed_origins():
        print("MEDIA_LEGACY_ALLOWED_ORIGINS is empty; refusing to run.")
        return 1

    failures: list[MigrationFailure] = []

    with httpx.Client(timeout=args.timeout_seconds) as client, Session(engine) as db:
        campaign_maps = db.exec(
            select(CampaignTacticalMap).where(CampaignTacticalMap.image_url.is_not(None))
        ).all()
        for map_config in campaign_maps:
            source_url = map_config.image_url or ""
            try:
                changed = _migrate_campaign_map(client, db, map_config)
                print(
                    f"[{'ok' if changed else 'skip'}] campaign-map:{map_config.id} "
                    f"{'map migrated' if changed else 'already managed'}"
                )
            except Exception as exc:
                db.rollback()
                failures.append(
                    MigrationFailure(
                        record_type="campaign_map",
                        record_id=map_config.id,
                        source_url=source_url,
                        reason=str(exc),
                    )
                )
                print(f"[fail] campaign-map:{map_config.id} {exc}")

        entities = db.exec(
            select(CampaignEntity).where(CampaignEntity.image_url.is_not(None))
        ).all()
        for entity in entities:
            source_url = entity.image_url or ""
            try:
                changed = _migrate_campaign_entity(client, db, entity)
                print(
                    f"[{'ok' if changed else 'skip'}] entity:{entity.id} "
                    f"{'image migrated' if changed else 'already managed'}"
                )
            except Exception as exc:
                db.rollback()
                failures.append(
                    MigrationFailure(
                        record_type="campaign_entity",
                        record_id=entity.id,
                        source_url=source_url,
                        reason=str(exc),
                    )
                )
                print(f"[fail] entity:{entity.id} {exc}")

    print(
        f"Completed media backfill with {len(failures)} failure(s)."
    )
    for failure in failures:
        print(
            f"- {failure.record_type}:{failure.record_id} "
            f"{failure.source_url} -> {failure.reason}"
        )
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
