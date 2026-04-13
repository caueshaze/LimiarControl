import unittest
from asyncio import run
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.routes.character_sheet_drafts_common import (
    create_party_character_sheet_draft_service,
    derive_party_character_sheet_draft_service,
    list_party_character_sheet_drafts_service,
    update_party_character_sheet_draft_service,
)
from app.api.routes.character_sheets_common import (
    accept_my_character_sheet_service,
    normalize_character_sheet_payload,
    publish_character_sheet_realtime_safe,
    publish_character_sheet_realtime,
    validate_character_sheet_payload,
    update_character_sheet_service,
)
from app.schemas.character_sheet import CharacterSheetRead
from app.services.dragonborn_ancestry import resolve_dragonborn_lineage_state
from app.services.draconic_ancestry import (
    get_draconic_damage_type,
    get_draconic_resistance_type,
)
from app.models.character_sheet import CharacterSheet
from app.models.party_character_sheet_draft import (
    PartyCharacterSheetDraft,
    PartyCharacterSheetDraftStatus,
)
from app.schemas.character_sheet import CharacterSheetUpdate
from app.schemas.character_sheet_draft import (
    PartyCharacterSheetDraftCreate,
    PartyCharacterSheetDraftDeriveRequest,
    PartyCharacterSheetDraftUpdate,
)


class CharacterSheetDraftServiceTests(unittest.TestCase):
    def test_create_party_character_sheet_draft_creates_active_entry(self):
        session = MagicMock()
        now = datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc)

        with patch(
            "app.api.routes.character_sheet_drafts_common.get_party_with_gm_check",
            return_value=SimpleNamespace(id="party-1"),
        ), patch(
            "app.api.routes.character_sheet_drafts_common.validate_character_sheet_payload",
        ), patch(
            "app.api.routes.character_sheet_drafts_common.normalize_character_sheet_payload",
            return_value={"name": "Draft Hero"},
        ), patch(
            "app.api.routes.character_sheet_drafts_common.utcnow",
            return_value=now,
        ):
            result = create_party_character_sheet_draft_service(
                "party-1",
                PartyCharacterSheetDraftCreate(
                    name=" Draft Hero ",
                    data={"name": "Draft Hero"},
                ),
                user=SimpleNamespace(id="gm-1"),
                session=session,
            )

        created_entry = session.add.call_args.args[0]
        self.assertIsInstance(created_entry, PartyCharacterSheetDraft)
        self.assertEqual(created_entry.party_id, "party-1")
        self.assertEqual(created_entry.created_by_user_id, "gm-1")
        self.assertEqual(created_entry.name, "Draft Hero")
        self.assertEqual(created_entry.status, PartyCharacterSheetDraftStatus.ACTIVE)
        self.assertEqual(created_entry.created_at, now)
        session.commit.assert_called_once_with()
        session.refresh.assert_called_once_with(created_entry)
        self.assertEqual(result.partyId, "party-1")
        self.assertEqual(result.status, "active")

    def test_list_party_character_sheet_drafts_orders_active_before_archived(self):
        session = MagicMock()
        older = datetime(2026, 3, 26, 10, 0, tzinfo=timezone.utc)
        newer = datetime(2026, 3, 27, 10, 0, tzinfo=timezone.utc)
        active_entry = PartyCharacterSheetDraft(
            id="draft-active",
            party_id="party-1",
            name="Active Draft",
            data={"name": "Hero"},
            status=PartyCharacterSheetDraftStatus.ACTIVE,
            created_by_user_id="gm-1",
            created_at=older,
            updated_at=newer,
        )
        archived_entry = PartyCharacterSheetDraft(
            id="draft-archived",
            party_id="party-1",
            name="Archived Draft",
            data={"name": "Hero"},
            status=PartyCharacterSheetDraftStatus.ARCHIVED,
            created_by_user_id="gm-1",
            created_at=newer,
            updated_at=None,
        )
        session.exec.return_value.all.return_value = [archived_entry, active_entry]

        with patch(
            "app.api.routes.character_sheet_drafts_common.get_party_with_gm_check",
            return_value=SimpleNamespace(id="party-1"),
        ):
            result = list_party_character_sheet_drafts_service(
                "party-1",
                user=SimpleNamespace(id="gm-1"),
                session=session,
            )

        self.assertEqual([entry.id for entry in result], ["draft-active", "draft-archived"])

    def test_derive_party_character_sheet_draft_creates_character_sheet_and_archives_draft(self):
        session = MagicMock()
        now = datetime(2026, 3, 27, 15, 0, tzinfo=timezone.utc)
        party = SimpleNamespace(id="party-1", campaign_id="campaign-1")
        draft = PartyCharacterSheetDraft(
            id="draft-1",
            party_id="party-1",
            name="Cleric Draft",
            data={"name": "Cleric"},
            status=PartyCharacterSheetDraftStatus.ACTIVE,
            created_by_user_id="gm-1",
            created_at=now,
            updated_at=None,
        )

        with patch(
            "app.api.routes.character_sheet_drafts_common.get_party_with_gm_check",
            return_value=party,
        ), patch(
            "app.api.routes.character_sheet_drafts_common.get_party_character_sheet_draft_or_404",
            return_value=draft,
        ), patch(
            "app.api.routes.character_sheet_drafts_common.require_joined_player",
        ), patch(
            "app.api.routes.character_sheet_drafts_common.get_character_sheet",
            return_value=None,
        ), patch(
            "app.api.routes.character_sheet_drafts_common.validate_character_sheet_payload",
        ), patch(
            "app.api.routes.character_sheet_drafts_common.normalize_character_sheet_payload",
            return_value={"name": "Cleric"},
        ), patch(
            "app.api.routes.character_sheet_drafts_common.sync_character_sheet_inventory",
        ) as mock_sync_inventory, patch(
            "app.api.routes.character_sheet_drafts_common.utcnow",
            return_value=now,
        ):
            result = derive_party_character_sheet_draft_service(
                "party-1",
                "draft-1",
                PartyCharacterSheetDraftDeriveRequest(playerUserId="player-1"),
                user=SimpleNamespace(id="gm-1"),
                session=session,
            )

        added_entries = [call.args[0] for call in session.add.call_args_list]
        created_sheet = next(entry for entry in added_entries if isinstance(entry, CharacterSheet))
        self.assertEqual(created_sheet.party_id, "party-1")
        self.assertEqual(created_sheet.player_user_id, "player-1")
        self.assertEqual(created_sheet.source_draft_id, "draft-1")
        self.assertEqual(created_sheet.delivered_by_user_id, "gm-1")
        self.assertEqual(created_sheet.delivered_at, now)
        self.assertIsNone(created_sheet.accepted_at)
        self.assertEqual(draft.status, PartyCharacterSheetDraftStatus.ARCHIVED)
        self.assertEqual(draft.archived_at, now)
        self.assertEqual(draft.last_derived_at, now)
        session.commit.assert_called_once_with()
        session.refresh.assert_called_once_with(created_sheet)
        mock_sync_inventory.assert_called_once_with(
            party=party,
            player_user_id="player-1",
            sheet_data={"name": "Cleric"},
            db=session,
        )
        self.assertEqual(result.playerId, "player-1")
        self.assertEqual(result.sourceDraftId, "draft-1")
        self.assertIsNone(result.acceptedAt)

    def test_derive_party_character_sheet_draft_rejects_existing_character_sheet(self):
        session = MagicMock()
        draft = PartyCharacterSheetDraft(
            id="draft-1",
            party_id="party-1",
            name="Cleric Draft",
            data={"name": "Cleric"},
            status=PartyCharacterSheetDraftStatus.ACTIVE,
            created_by_user_id="gm-1",
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

        with patch(
            "app.api.routes.character_sheet_drafts_common.get_party_with_gm_check",
            return_value=SimpleNamespace(id="party-1", campaign_id="campaign-1"),
        ), patch(
            "app.api.routes.character_sheet_drafts_common.get_party_character_sheet_draft_or_404",
            return_value=draft,
        ), patch(
            "app.api.routes.character_sheet_drafts_common.require_joined_player",
        ), patch(
            "app.api.routes.character_sheet_drafts_common.get_character_sheet",
            return_value=SimpleNamespace(id="sheet-1"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                derive_party_character_sheet_draft_service(
                    "party-1",
                    "draft-1",
                    PartyCharacterSheetDraftDeriveRequest(playerUserId="player-1"),
                    user=SimpleNamespace(id="gm-1"),
                    session=session,
                )

        self.assertEqual(ctx.exception.status_code, 409)
        session.commit.assert_not_called()

    def test_update_party_character_sheet_draft_rejects_archived_entry(self):
        session = MagicMock()
        draft = PartyCharacterSheetDraft(
            id="draft-1",
            party_id="party-1",
            name="Archived Draft",
            data={"name": "Cleric"},
            status=PartyCharacterSheetDraftStatus.ARCHIVED,
            created_by_user_id="gm-1",
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

        with patch(
            "app.api.routes.character_sheet_drafts_common.get_party_with_gm_check",
            return_value=SimpleNamespace(id="party-1"),
        ), patch(
            "app.api.routes.character_sheet_drafts_common.get_party_character_sheet_draft_or_404",
            return_value=draft,
        ):
            with self.assertRaises(HTTPException) as ctx:
                update_party_character_sheet_draft_service(
                    "party-1",
                    "draft-1",
                    PartyCharacterSheetDraftUpdate(
                        name=" Updated Draft ",
                        data={"name": "Updated Hero"},
                    ),
                    user=SimpleNamespace(id="gm-1"),
                    session=session,
                )

        self.assertEqual(ctx.exception.status_code, 409)
        session.commit.assert_not_called()


class CharacterSheetAcceptanceTests(unittest.TestCase):
    def test_accept_my_character_sheet_marks_sheet_as_accepted(self):
        session = MagicMock()
        accepted_at = datetime(2026, 3, 27, 18, 30, tzinfo=timezone.utc)
        entry = CharacterSheet(
            id="sheet-1",
            party_id="party-1",
            player_user_id="player-1",
            data={"name": "Hero"},
            created_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
            updated_at=None,
            accepted_at=None,
        )

        with patch(
            "app.api.routes.character_sheets_common.require_party_member",
            return_value=SimpleNamespace(id="party-1"),
        ), patch(
            "app.api.routes.character_sheets_common.get_character_sheet_or_404",
            return_value=entry,
        ), patch(
            "app.api.routes.character_sheets_common.user_id",
            return_value="player-1",
        ), patch(
            "app.api.routes.character_sheets_common.utcnow",
            return_value=accepted_at,
        ):
            result = accept_my_character_sheet_service(
                "party-1",
                user=SimpleNamespace(id="player-1"),
                session=session,
            )

        self.assertEqual(entry.accepted_at, accepted_at)
        session.add.assert_called_once_with(entry)
        session.commit.assert_called_once_with()
        session.refresh.assert_called_once_with(entry)
        self.assertEqual(result.acceptedAt, accepted_at)

    def test_publish_character_sheet_realtime_emits_campaign_event(self):
        record = CharacterSheetRead(
            id="sheet-1",
            partyId="party-1",
            playerId="player-1",
            data={"name": "Hero"},
            sourceDraftId="draft-1",
            deliveredByUserId="gm-1",
            deliveredAt=datetime(2026, 3, 27, 18, 0, tzinfo=timezone.utc),
            acceptedAt=None,
            createdAt=datetime(2026, 3, 27, 18, 0, tzinfo=timezone.utc),
            updatedAt=None,
        )

        with patch(
            "app.api.routes.character_sheets_common.centrifugo.publish",
            new=AsyncMock(),
        ) as mock_publish:
            run(
                publish_character_sheet_realtime(
                    "campaign-1",
                    "party-1",
                    record,
                    "delivered",
                )
            )

        mock_publish.assert_awaited_once()
        channel, event = mock_publish.await_args.args
        self.assertEqual(channel, "campaign:campaign-1")
        self.assertEqual(event["type"], "character_sheet_updated")
        self.assertEqual(event["payload"]["partyId"], "party-1")
        self.assertEqual(event["payload"]["playerUserId"], "player-1")
        self.assertEqual(event["payload"]["updateKind"], "delivered")

    def test_publish_character_sheet_realtime_safe_swallows_publish_errors(self):
        record = CharacterSheetRead(
            id="sheet-1",
            partyId="party-1",
            playerId="player-1",
            data={"name": "Hero"},
            sourceDraftId="draft-1",
            deliveredByUserId="gm-1",
            deliveredAt=datetime(2026, 3, 27, 18, 0, tzinfo=timezone.utc),
            acceptedAt=None,
            createdAt=datetime(2026, 3, 27, 18, 0, tzinfo=timezone.utc),
            updatedAt=None,
        )

        with patch(
            "app.api.routes.character_sheets_common.publish_character_sheet_realtime",
            new=AsyncMock(side_effect=RuntimeError("centrifugo unavailable")),
        ), patch(
            "app.api.routes.character_sheets_common.logger.exception",
        ) as mock_logger:
            run(
                publish_character_sheet_realtime_safe(
                    "campaign-1",
                    "party-1",
                    record,
                    "accepted",
                )
            )

        mock_logger.assert_called_once()

    def test_validate_character_sheet_payload_requires_draconic_ancestry(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_character_sheet_payload(
                {
                    "class": "sorcerer",
                    "subclass": "draconic_bloodline",
                    "subclassConfig": None,
                    "race": "human",
                    "raceConfig": None,
                }
            )

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            ctx.exception.detail,
            "draconicAncestry is required for Draconic Bloodline",
        )

    def test_validate_character_sheet_payload_rejects_invalid_draconic_ancestry(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_character_sheet_payload(
                {
                    "class": "sorcerer",
                    "subclass": "draconic_bloodline",
                    "subclassConfig": {"draconicAncestry": "shadow"},
                    "race": "human",
                    "raceConfig": None,
                }
            )

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            ctx.exception.detail,
            "draconicAncestry is invalid for Draconic Bloodline",
        )

    def test_validate_character_sheet_payload_requires_dragonborn_draconic_ancestry(self):
        with self.assertRaises(HTTPException) as ctx:
            validate_character_sheet_payload(
                {
                    "class": "fighter",
                    "subclass": None,
                    "subclassConfig": None,
                    "race": "dragonborn",
                    "raceConfig": None,
                }
            )

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(
            ctx.exception.detail,
            "draconicAncestry is required for dragonborn",
        )

    def test_validate_character_sheet_payload_accepts_valid_draconic_ancestry(self):
        validate_character_sheet_payload(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "subclassConfig": {"draconicAncestry": "blue"},
                "race": "human",
                "raceConfig": None,
            }
        )

    def test_normalize_character_sheet_payload_migrates_legacy_dragon_ancestor_key(self):
        normalized = normalize_character_sheet_payload(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "subclassConfig": {"dragonAncestor": "red"},
                "race": "human",
                "raceConfig": None,
            }
        )

        self.assertEqual(
            normalized["subclassConfig"],
            {"draconicAncestry": "red"},
        )

    def test_normalize_character_sheet_payload_keeps_canonical_draconic_ancestry_key(self):
        normalized = normalize_character_sheet_payload(
            {
                "class": "sorcerer",
                "subclass": "draconic_bloodline",
                "subclassConfig": {"draconicAncestry": "blue"},
                "race": "human",
                "raceConfig": None,
            }
        )

        self.assertEqual(
            normalized["subclassConfig"],
            {"draconicAncestry": "blue"},
        )

    def test_normalize_character_sheet_payload_migrates_legacy_dragonborn_ancestry_key(self):
        normalized = normalize_character_sheet_payload(
            {
                "class": "fighter",
                "subclass": None,
                "subclassConfig": None,
                "race": "dragonborn",
                "raceConfig": {"dragonbornAncestry": "red"},
            }
        )

        self.assertEqual(
            normalized["raceConfig"],
            {"draconicAncestry": "red"},
        )

    def test_normalize_character_sheet_payload_keeps_canonical_dragonborn_draconic_ancestry_key(self):
        normalized = normalize_character_sheet_payload(
            {
                "class": "fighter",
                "subclass": None,
                "subclassConfig": None,
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "blue"},
            }
        )

        self.assertEqual(
            normalized["raceConfig"],
            {"draconicAncestry": "blue"},
        )

    def test_draconic_ancestry_maps_to_damage_type(self):
        self.assertEqual(get_draconic_damage_type("red"), "fire")
        self.assertEqual(get_draconic_damage_type("silver"), "cold")
        self.assertEqual(get_draconic_damage_type("blue"), "lightning")

    def test_draconic_ancestry_maps_to_resistance_type(self):
        self.assertEqual(get_draconic_resistance_type("red"), "fire")
        self.assertEqual(get_draconic_resistance_type("green"), "poison")
        self.assertEqual(get_draconic_resistance_type("white"), "cold")

    def test_dragonborn_lineage_exposes_breath_weapon_data(self):
        lineage = resolve_dragonborn_lineage_state(
            {
                "race": "dragonborn",
                "raceConfig": {"draconicAncestry": "white"},
            }
        )

        self.assertEqual(lineage["damageType"], "cold")
        self.assertEqual(lineage["resistanceType"], "cold")
        self.assertEqual(lineage["breathWeaponShape"], "cone")
        self.assertEqual(lineage["breathWeaponSaveType"], "constitution")

    def test_update_character_sheet_service_rejects_accepted_sheet(self):
        session = MagicMock()
        entry = CharacterSheet(
            id="sheet-1",
            party_id="party-1",
            player_user_id="player-1",
            data={"name": "Hero"},
            created_at=datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
            updated_at=None,
            accepted_at=datetime(2026, 3, 27, 14, 0, tzinfo=timezone.utc),
        )

        with patch(
            "app.api.routes.character_sheets_common.require_party_member",
            return_value=SimpleNamespace(id="party-1"),
        ), patch(
            "app.api.routes.character_sheets_common.user_id",
            return_value="player-1",
        ), patch(
            "app.api.routes.character_sheets_common.get_character_sheet_or_404",
            return_value=entry,
        ):
            with self.assertRaises(HTTPException) as ctx:
                update_character_sheet_service(
                    "party-1",
                    CharacterSheetUpdate(data={"name": "Updated Hero"}),
                    user=SimpleNamespace(id="player-1"),
                    session=session,
                )

        self.assertEqual(ctx.exception.status_code, 409)
        session.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
