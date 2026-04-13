from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_MB = 30
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
TEMP_ENTITY_ASSET_MAX_AGE_HOURS = 24
MANAGED_ASSET_BASE_PATH = "/api/assets"
DEFAULT_CACHE_CONTROL = "private, max-age=60"

_IMAGE_FORMAT_CONTENT_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "GIF": "image/gif",
}
_ASSET_ID_PATTERN = r"(?P<asset_id>[a-f0-9]{32})"
_CAMPAIGN_ID_PATTERN = r"(?P<campaign_id>[^/]+)"
_ENTITY_ID_PATTERN = r"(?P<entity_id>[^/]+)"
_MAP_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/maps/{_ASSET_ID_PATTERN}$"
)
_ENTITY_TEMP_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/entities/tmp/{_ASSET_ID_PATTERN}$"
)
_ENTITY_FINAL_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/entities/{_ENTITY_ID_PATTERN}/{_ASSET_ID_PATTERN}$"
)


@dataclass(frozen=True)
class ManagedAssetRef:
    kind: Literal["campaign_map", "entity_temp", "entity_final"]
    campaign_id: str
    asset_id: str
    entity_id: str | None = None

    @property
    def object_key(self) -> str:
        if self.kind == "campaign_map":
            return f"campaigns/{self.campaign_id}/maps/{self.asset_id}"
        if self.kind == "entity_temp":
            return f"campaigns/{self.campaign_id}/entities/tmp/{self.asset_id}"
        if not self.entity_id:
            raise ValueError("Entity asset is missing an entity id")
        return f"campaigns/{self.campaign_id}/entities/{self.entity_id}/{self.asset_id}"

    @property
    def url(self) -> str:
        if self.kind == "campaign_map":
            return (
                f"{MANAGED_ASSET_BASE_PATH}/campaigns/{self.campaign_id}/maps/{self.asset_id}"
            )
        if self.kind == "entity_temp":
            return (
                f"{MANAGED_ASSET_BASE_PATH}/campaigns/{self.campaign_id}/entities/tmp/{self.asset_id}"
            )
        if not self.entity_id:
            raise ValueError("Entity asset is missing an entity id")
        return (
            f"{MANAGED_ASSET_BASE_PATH}/campaigns/{self.campaign_id}/entities/"
            f"{self.entity_id}/{self.asset_id}"
        )


@dataclass(frozen=True)
class ManagedObjectHeaders:
    content_type: str
    content_length: int | None
    cache_control: str
    etag: str | None
    last_modified: datetime | None


@dataclass
class ManagedObjectStream:
    response: object
    headers: ManagedObjectHeaders


def _normalize_content_type(content_type: str | None) -> str:
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    return normalized


def _normalize_endpoint(endpoint: str, secure: bool) -> tuple[str, bool]:
    normalized = endpoint.strip()
    if normalized.startswith("http://") or normalized.startswith("https://"):
        parsed = urlparse(normalized)
        if not parsed.netloc:
            raise RuntimeError("Invalid MINIO_ENDPOINT")
        return parsed.netloc, parsed.scheme == "https"
    if not normalized:
        raise RuntimeError("MINIO_ENDPOINT is not configured")
    return normalized, secure


def _client() -> Minio:
    endpoint, secure = _normalize_endpoint(settings.minio_endpoint, settings.minio_secure)
    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=secure,
    )


def build_campaign_map_asset_ref(
    campaign_id: str,
    asset_id: str | None = None,
) -> ManagedAssetRef:
    return ManagedAssetRef(
        kind="campaign_map",
        campaign_id=campaign_id,
        asset_id=asset_id or uuid4().hex,
    )


def build_entity_temp_asset_ref(
    campaign_id: str,
    asset_id: str | None = None,
) -> ManagedAssetRef:
    return ManagedAssetRef(
        kind="entity_temp",
        campaign_id=campaign_id,
        asset_id=asset_id or uuid4().hex,
    )


def build_entity_asset_ref(
    campaign_id: str,
    entity_id: str,
    asset_id: str | None = None,
) -> ManagedAssetRef:
    return ManagedAssetRef(
        kind="entity_final",
        campaign_id=campaign_id,
        entity_id=entity_id,
        asset_id=asset_id or uuid4().hex,
    )


def parse_managed_url(url: str) -> ManagedAssetRef:
    if not isinstance(url, str):
        raise ValueError("Managed asset URL must be a string")
    if not url or url.strip() != url or "?" in url or "#" in url:
        raise ValueError("Managed asset URL must use the canonical app-managed format")

    match = _MAP_URL_RE.fullmatch(url)
    if match:
        return ManagedAssetRef(
            kind="campaign_map",
            campaign_id=match.group("campaign_id"),
            asset_id=match.group("asset_id"),
        )

    match = _ENTITY_TEMP_URL_RE.fullmatch(url)
    if match:
        return ManagedAssetRef(
            kind="entity_temp",
            campaign_id=match.group("campaign_id"),
            asset_id=match.group("asset_id"),
        )

    match = _ENTITY_FINAL_URL_RE.fullmatch(url)
    if match:
        return ManagedAssetRef(
            kind="entity_final",
            campaign_id=match.group("campaign_id"),
            entity_id=match.group("entity_id"),
            asset_id=match.group("asset_id"),
        )

    raise ValueError("Managed asset URL must use the canonical app-managed format")


def is_managed_url(url: str | None) -> bool:
    if not url:
        return False
    try:
        parse_managed_url(url)
    except ValueError:
        return False
    return True


def ensure_bucket_exists() -> bool:
    try:
        client = _client()
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        return True
    except Exception:
        logger.exception("Failed to ensure MinIO bucket exists")
        return False


def _load_and_validate_image(
    file_bytes: bytes,
    content_type: str,
) -> tuple[Image.Image, str]:
    normalized_type = _normalize_content_type(content_type)
    if normalized_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Tipo de arquivo não suportado: {normalized_type or content_type}. Use JPEG, PNG, WebP ou GIF."
        )
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"Arquivo muito grande. O tamanho máximo é {MAX_FILE_SIZE_MB} MB."
        )

    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Arquivo de imagem inválido ou corrompido.") from exc

    actual_content_type = _IMAGE_FORMAT_CONTENT_TYPES.get((image.format or "").upper())
    if actual_content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Formato de imagem não suportado.")
    if actual_content_type != normalized_type:
        raise ValueError("O tipo enviado não corresponde ao conteúdo real do arquivo.")
    return image, actual_content_type


def _put_object(object_ref: ManagedAssetRef, payload: bytes, content_type: str) -> str:
    if not ensure_bucket_exists():
        raise RuntimeError("MinIO não está disponível no servidor.")
    client = _client()
    client.put_object(
        settings.minio_bucket,
        object_ref.object_key,
        io.BytesIO(payload),
        len(payload),
        content_type=content_type,
    )
    return object_ref.url


def upload_map_image(file_bytes: bytes, content_type: str, campaign_id: str) -> str:
    _image, actual_content_type = _load_and_validate_image(file_bytes, content_type)
    object_ref = build_campaign_map_asset_ref(campaign_id)
    return _put_object(object_ref, file_bytes, actual_content_type)


def upload_entity_image(file_bytes: bytes, content_type: str, campaign_id: str) -> str:
    image, _actual_content_type = _load_and_validate_image(file_bytes, content_type)
    normalized = ImageOps.exif_transpose(image)
    if normalized.mode not in {"RGB", "RGBA"}:
        normalized = normalized.convert("RGBA")
    fitted = ImageOps.fit(normalized, (512, 512), method=Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    fitted.save(buffer, format="WEBP", quality=90)
    object_ref = build_entity_temp_asset_ref(campaign_id)
    return _put_object(object_ref, buffer.getvalue(), "image/webp")


def stat_object(object_ref: ManagedAssetRef):
    client = _client()
    return client.stat_object(settings.minio_bucket, object_ref.object_key)


def assert_managed_asset_exists(object_ref: ManagedAssetRef) -> None:
    try:
        stat_object(object_ref)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            raise FileNotFoundError(object_ref.object_key) from exc
        raise


def get_object_stream(object_ref: ManagedAssetRef) -> ManagedObjectStream:
    client = _client()
    try:
        stat = client.stat_object(settings.minio_bucket, object_ref.object_key)
        response = client.get_object(settings.minio_bucket, object_ref.object_key)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            raise FileNotFoundError(object_ref.object_key) from exc
        raise
    headers = ManagedObjectHeaders(
        content_type=response.headers.get("Content-Type", "application/octet-stream"),
        content_length=getattr(stat, "size", None),
        cache_control=DEFAULT_CACHE_CONTROL,
        etag=getattr(stat, "etag", None),
        last_modified=getattr(stat, "last_modified", None),
    )
    return ManagedObjectStream(response=response, headers=headers)


def copy_object(source_ref: ManagedAssetRef, target_ref: ManagedAssetRef) -> None:
    client = _client()
    client.copy_object(
        settings.minio_bucket,
        target_ref.object_key,
        CopySource(settings.minio_bucket, source_ref.object_key),
    )


def delete_object(object_ref: ManagedAssetRef) -> None:
    client = _client()
    client.remove_object(settings.minio_bucket, object_ref.object_key)


def delete_managed_url_best_effort(url: str | None) -> None:
    if not url or not is_managed_url(url):
        return
    try:
        delete_object(parse_managed_url(url))
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject", "NoSuchBucket"}:
            return
        logger.warning("Failed to delete managed asset %s: %s", url, exc)
    except Exception:
        logger.exception("Failed to delete managed asset %s", url)


def delete_campaign_prefix_best_effort(campaign_id: str) -> None:
    prefix = f"campaigns/{campaign_id}/"
    try:
        client = _client()
        for entry in client.list_objects(
            settings.minio_bucket,
            prefix=prefix,
            recursive=True,
        ):
            client.remove_object(settings.minio_bucket, entry.object_name)
    except S3Error as exc:
        if exc.code == "NoSuchBucket":
            return
        logger.warning("Failed to delete media prefix %s: %s", prefix, exc)
    except Exception:
        logger.exception("Failed to delete media prefix %s", prefix)


def cleanup_expired_temporary_assets(max_age_hours: int = TEMP_ENTITY_ASSET_MAX_AGE_HOURS) -> int:
    prefix = "campaigns/"
    removed = 0
    cutoff = datetime.now(UTC) - timedelta(hours=max_age_hours)
    try:
        client = _client()
        for entry in client.list_objects(
            settings.minio_bucket,
            prefix=prefix,
            recursive=True,
        ):
            if "/entities/tmp/" not in entry.object_name:
                continue
            last_modified = getattr(entry, "last_modified", None)
            if last_modified is None or last_modified >= cutoff:
                continue
            try:
                client.remove_object(settings.minio_bucket, entry.object_name)
                removed += 1
            except Exception:
                logger.exception(
                    "Failed to remove expired temporary asset %s", entry.object_name
                )
    except S3Error as exc:
        if exc.code != "NoSuchBucket":
            logger.warning("Failed to scan temporary assets: %s", exc)
    except Exception:
        logger.exception("Failed to scan temporary assets")
    return removed


def stream_object_chunks(stream: object, chunk_size: int = 64 * 1024):
    try:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            yield chunk
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
        release_conn = getattr(stream, "release_conn", None)
        if callable(release_conn):
            release_conn()


def build_asset_response_headers(headers: ManagedObjectHeaders) -> dict[str, str]:
    response_headers = {"Cache-Control": headers.cache_control}
    if headers.content_length is not None:
        response_headers["Content-Length"] = str(headers.content_length)
    if headers.etag:
        response_headers["ETag"] = (
            headers.etag if headers.etag.startswith('"') else f'"{headers.etag}"'
        )
    if headers.last_modified is not None:
        response_headers["Last-Modified"] = format_datetime(
            headers.last_modified.astimezone(UTC),
            usegmt=True,
        )
    return response_headers
