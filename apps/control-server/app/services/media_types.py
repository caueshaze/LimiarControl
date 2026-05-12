from __future__ import annotations

from datetime import datetime
import logging
import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse
from uuid import uuid4

from minio import Minio

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
_USER_ID_PATTERN = r"(?P<user_id>[^/]+)"
_MAP_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/maps/{_ASSET_ID_PATTERN}$"
)
_ENTITY_TEMP_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/entities/tmp/{_ASSET_ID_PATTERN}$"
)
_ENTITY_FINAL_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/campaigns/{_CAMPAIGN_ID_PATTERN}/entities/{_ENTITY_ID_PATTERN}/{_ASSET_ID_PATTERN}$"
)
_USER_AVATAR_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/users/{_USER_ID_PATTERN}/avatar/{_ASSET_ID_PATTERN}$"
)
_USER_TOKEN_URL_RE = re.compile(
    rf"^{re.escape(MANAGED_ASSET_BASE_PATH)}/users/{_USER_ID_PATTERN}/token/{_ASSET_ID_PATTERN}$"
)


@dataclass(frozen=True)
class ManagedAssetRef:
    kind: Literal["campaign_map", "entity_temp", "entity_final", "user_avatar", "user_token"]
    campaign_id: str | None = None
    asset_id: str = ""
    entity_id: str | None = None
    user_id: str | None = None

    @property
    def object_key(self) -> str:
        if self.kind == "campaign_map":
            return f"campaigns/{self.campaign_id}/maps/{self.asset_id}"
        if self.kind == "entity_temp":
            return f"campaigns/{self.campaign_id}/entities/tmp/{self.asset_id}"
        if self.kind == "user_avatar":
            if not self.user_id:
                raise ValueError("User asset is missing a user id")
            return f"users/{self.user_id}/avatar/{self.asset_id}"
        if self.kind == "user_token":
            if not self.user_id:
                raise ValueError("User asset is missing a user id")
            return f"users/{self.user_id}/token/{self.asset_id}"
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
        if self.kind == "user_avatar":
            if not self.user_id:
                raise ValueError("User asset is missing a user id")
            return f"{MANAGED_ASSET_BASE_PATH}/users/{self.user_id}/avatar/{self.asset_id}"
        if self.kind == "user_token":
            if not self.user_id:
                raise ValueError("User asset is missing a user id")
            return f"{MANAGED_ASSET_BASE_PATH}/users/{self.user_id}/token/{self.asset_id}"
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


def build_user_avatar_asset_ref(
    user_id: str,
    asset_id: str | None = None,
) -> ManagedAssetRef:
    return ManagedAssetRef(
        kind="user_avatar",
        user_id=user_id,
        asset_id=asset_id or uuid4().hex,
    )


def build_user_token_asset_ref(
    user_id: str,
    asset_id: str | None = None,
) -> ManagedAssetRef:
    return ManagedAssetRef(
        kind="user_token",
        user_id=user_id,
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

    match = _USER_AVATAR_URL_RE.fullmatch(url)
    if match:
        return ManagedAssetRef(
            kind="user_avatar",
            user_id=match.group("user_id"),
            asset_id=match.group("asset_id"),
        )

    match = _USER_TOKEN_URL_RE.fullmatch(url)
    if match:
        return ManagedAssetRef(
            kind="user_token",
            user_id=match.group("user_id"),
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
