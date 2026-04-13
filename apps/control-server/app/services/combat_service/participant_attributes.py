from __future__ import annotations

from app.models.campaign_entity import CampaignEntity
from app.services.wild_shape_catalog import get_form


def resolve_player_size(state_json: dict) -> str | None:
    wild_shape = state_json.get("wildShape")
    if isinstance(wild_shape, dict) and wild_shape.get("active"):
        form_key = wild_shape.get("formKey")
        if isinstance(form_key, str) and form_key.strip():
            form = get_form(form_key)
            if form is not None and isinstance(form.size, str):
                return form.size

    value = state_json.get("size")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def resolve_entity_size(
    overrides: dict,
    campaign_entity: CampaignEntity | None,
) -> str | None:
    for key in ("size", "sizeCategory", "size_category"):
        value = overrides.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    if campaign_entity is not None and isinstance(campaign_entity.size, str):
        if campaign_entity.size.strip():
            return campaign_entity.size.strip()
    return None


def resolve_player_movement_speed(state_json: dict) -> int | None:
    wild_shape = state_json.get("wildShape")
    if isinstance(wild_shape, dict) and wild_shape.get("active"):
        form_key = wild_shape.get("formKey")
        if isinstance(form_key, str) and form_key.strip():
            form = get_form(form_key)
            if form is not None and form.speed_meters > 0:
                return form.speed_meters

    for key in ("speedMeters", "speed_meters"):
        value = state_json.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return None


def resolve_entity_movement_speed(
    overrides: dict,
    campaign_entity: CampaignEntity | None,
) -> int | None:
    for key in ("speedMeters", "speed_meters", "movementSpeedBase"):
        value = overrides.get(key)
        if isinstance(value, int) and value > 0:
            return value

    if campaign_entity is not None and isinstance(campaign_entity.speed_meters, int):
        if campaign_entity.speed_meters > 0:
            return campaign_entity.speed_meters
    return None
