from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _enum_values(enum_cls: type[Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class PartyCharacterSheetDraftStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class PartyCharacterSheetDraft(SQLModel, table=True):
    __tablename__ = "party_character_sheet_draft"  # type: ignore[assignment]

    id: str = Field(primary_key=True)
    party_id: str = Field(foreign_key="party.id", index=True)
    name: str
    data: dict = Field(sa_column=Column(JSONB, nullable=False))
    status: PartyCharacterSheetDraftStatus = Field(
        default=PartyCharacterSheetDraftStatus.ACTIVE,
        sa_column=Column(
            SAEnum(
                PartyCharacterSheetDraftStatus,
                name="partycharactersheetdraftstatus",
                values_callable=_enum_values,
            ),
            nullable=False,
            server_default=PartyCharacterSheetDraftStatus.ACTIVE.value,
        ),
    )
    created_by_user_id: str = Field(foreign_key="app_user.id", index=True)
    archived_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    last_derived_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
