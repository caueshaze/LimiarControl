from __future__ import annotations

import logging

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.campaign_spell import CampaignSpell
from app.services.base_spells import get_base_spell_by_canonical_key

from .exceptions import CombatServiceError

logger = logging.getLogger("app.services.combat_service.core")


class CombatSpellLookupMixin:

    @classmethod
    def _get_spell_catalog_entry_for_session(
        cls,
        db: Session,
        session_id: str,
        canonical_key: str,
    ):
        normalized_key = canonical_key.strip().lower()
        if not normalized_key:
            raise CombatServiceError("Spell canonical key is required.", 400)

        session_entry = cls._get_session_entry(db, session_id)
        if not session_entry:
            raise CombatServiceError("Session not found", 404)

        campaign_spell = db.exec(
            select(CampaignSpell).where(
                CampaignSpell.campaign_id == session_entry.campaign_id,
                CampaignSpell.is_enabled == True,
                func.lower(CampaignSpell.canonical_key) == normalized_key,
            )
        ).first()
        if campaign_spell:
            return campaign_spell

        base_spell = get_base_spell_by_canonical_key(
            db=db,
            system=cls._get_campaign_system_for_session(db, session_id),
            canonical_key=canonical_key,
        )
        if not base_spell:
            raise CombatServiceError(
                "Referenced spellCanonicalKey was not found in the catalog."
            )
        return base_spell

    @classmethod
    def _resolve_player_spell_entry(
        cls,
        data: dict,
        *,
        spell_canonical_key: str | None,
        spell_name: str | None = None,
        campaign_spell_id: str | None = None,
    ) -> dict:
        spellcasting = cls._as_dict(data.get("spellcasting"))
        spells = spellcasting.get("spells")
        if not isinstance(spells, list):
            raise CombatServiceError("Player has no spellcasting configured.", 400)

        canonical_lookup = cls._normalize_lookup(spell_canonical_key)
        name_lookup = cls._normalize_lookup(spell_name)
        campaign_id_lookup = cls._normalize_lookup(campaign_spell_id)

        if campaign_id_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("campaignSpellId")) == campaign_id_lookup:
                    return raw_spell

        if canonical_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("canonicalKey")) == canonical_lookup:
                    logger.debug(
                        "character sheet spell resolved via legacy canonicalKey fallback",
                        extra={"canonical_key": spell_canonical_key},
                    )
                    return raw_spell

        effective_name_lookup = name_lookup or canonical_lookup
        if effective_name_lookup:
            for raw_spell in spells:
                if not isinstance(raw_spell, dict):
                    continue
                if cls._normalize_lookup(raw_spell.get("name")) == effective_name_lookup:
                    logger.debug(
                        "character sheet spell resolved via legacy name fallback",
                        extra={"spell_name": spell_name or spell_canonical_key},
                    )
                    return raw_spell

        raise CombatServiceError("Spell is not available on the player's sheet.", 400)
