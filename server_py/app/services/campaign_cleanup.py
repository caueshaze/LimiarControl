from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, inspect
from sqlmodel import Session, select

from app.models.campaign import Campaign
from app.models.campaign_entity import CampaignEntity
from app.models.campaign_member import CampaignMember
from app.models.campaign_spell import CampaignSpell
from app.models.character_sheet import CharacterSheet
from app.models.combat import CombatState
from app.models.inventory import InventoryItem
from app.models.item import Item
from app.models.party import Party
from app.models.party_character_sheet_draft import PartyCharacterSheetDraft
from app.models.party_member import PartyMember
from app.models.purchase_event import PurchaseEvent
from app.models.roll_event import RollEvent
from app.models.session import Session as CampaignSession
from app.models.session_command_event import SessionCommandEvent
from app.models.session_entity import SessionEntity
from app.models.session_runtime import SessionRuntime
from app.models.session_state import SessionState


def _require_identifier(value: str | None, detail: str) -> str:
    if value is None:
        raise ValueError(detail)
    return value


def _delete_where_ids(
    db: Session,
    model,
    column,
    ids: Sequence[str],
    existing_tables: set[str],
) -> None:
    if not ids or model.__table__.name not in existing_tables:
        return
    db.exec(delete(model).where(column.in_(ids)))


def _delete_where(
    db: Session,
    model,
    clause,
    existing_tables: set[str],
) -> None:
    if model.__table__.name not in existing_tables:
        return
    db.exec(delete(model).where(clause))


def _existing_tables(db: Session) -> set[str]:
    return set(inspect(db.get_bind()).get_table_names())


def _session_ids_for_party(db: Session, party_id: str) -> list[str]:
    return [
        session_id
        for session_id in db.exec(
            select(CampaignSession.id).where(CampaignSession.party_id == party_id)
        ).all()
        if session_id
    ]


def _session_ids_for_campaign(db: Session, campaign_id: str) -> list[str]:
    return [
        session_id
        for session_id in db.exec(
            select(CampaignSession.id).where(CampaignSession.campaign_id == campaign_id)
        ).all()
        if session_id
    ]


def _party_ids_for_campaign(db: Session, campaign_id: str) -> list[str]:
    return [
        party_id
        for party_id in db.exec(
            select(Party.id).where(Party.campaign_id == campaign_id)
        ).all()
        if party_id
    ]


def _delete_session_tree(
    db: Session,
    session_ids: Sequence[str],
    existing_tables: set[str],
) -> None:
    _delete_where_ids(db, CombatState, CombatState.session_id, session_ids, existing_tables)
    _delete_where_ids(db, SessionRuntime, SessionRuntime.session_id, session_ids, existing_tables)
    _delete_where_ids(
        db, SessionCommandEvent, SessionCommandEvent.session_id, session_ids, existing_tables
    )
    _delete_where_ids(db, SessionState, SessionState.session_id, session_ids, existing_tables)
    _delete_where_ids(db, SessionEntity, SessionEntity.session_id, session_ids, existing_tables)
    _delete_where_ids(db, PurchaseEvent, PurchaseEvent.session_id, session_ids, existing_tables)
    _delete_where_ids(db, RollEvent, RollEvent.session_id, session_ids, existing_tables)
    _delete_where_ids(db, CampaignSession, CampaignSession.id, session_ids, existing_tables)


def delete_party_tree(db: Session, party: Party) -> None:
    party_id = _require_identifier(party.id, "Party is missing an id")
    session_ids = _session_ids_for_party(db, party_id)
    existing_tables = _existing_tables(db)

    _delete_session_tree(db, session_ids, existing_tables)
    _delete_where(db, CharacterSheet, CharacterSheet.party_id == party_id, existing_tables)
    _delete_where(db, PartyCharacterSheetDraft, PartyCharacterSheetDraft.party_id == party_id, existing_tables)
    _delete_where(db, InventoryItem, InventoryItem.party_id == party_id, existing_tables)
    _delete_where(db, PartyMember, PartyMember.party_id == party_id, existing_tables)
    _delete_where(db, Party, Party.id == party_id, existing_tables)


def delete_campaign_tree(db: Session, campaign: Campaign) -> None:
    campaign_id = _require_identifier(campaign.id, "Campaign is missing an id")
    session_ids = _session_ids_for_campaign(db, campaign_id)
    party_ids = _party_ids_for_campaign(db, campaign_id)
    existing_tables = _existing_tables(db)

    _delete_session_tree(db, session_ids, existing_tables)
    _delete_where(db, InventoryItem, InventoryItem.campaign_id == campaign_id, existing_tables)

    if party_ids:
        _delete_where(db, CharacterSheet, CharacterSheet.party_id.in_(party_ids), existing_tables)
        _delete_where(
            db,
            PartyCharacterSheetDraft,
            PartyCharacterSheetDraft.party_id.in_(party_ids),
            existing_tables,
        )
        _delete_where(db, PartyMember, PartyMember.party_id.in_(party_ids), existing_tables)
        _delete_where(db, Party, Party.id.in_(party_ids), existing_tables)

    _delete_where(db, RollEvent, RollEvent.campaign_id == campaign_id, existing_tables)
    _delete_where(db, CampaignSpell, CampaignSpell.campaign_id == campaign_id, existing_tables)
    _delete_where(db, Item, Item.campaign_id == campaign_id, existing_tables)
    _delete_where(db, CampaignEntity, CampaignEntity.campaign_id == campaign_id, existing_tables)
    _delete_where(db, CampaignMember, CampaignMember.campaign_id == campaign_id, existing_tables)
    _delete_where(db, Campaign, Campaign.id == campaign_id, existing_tables)
