import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from pydantic import ValidationError

from app.api.routes.campaigns import (
    create_campaign_map_config,
    delete_campaign_map_config,
    update_campaign_map_config,
)
from app.schemas.campaign import (
    CampaignMapConfigCreate,
    CampaignMapConfigUpdate,
    BlockedCell,
    decode_blocked_cells,
    encode_blocked_cells,
)


class CampaignMapConfigTests(unittest.TestCase):
    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.assert_managed_asset_exists")
    @patch("app.api.routes.campaigns.require_gm")
    def test_create_campaign_map_config_persists_trimmed_payload(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        _mock_delete_managed_url,
    ):
        campaign = SimpleNamespace(
            id="campaign-1",
        )
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        created_at = datetime.now(UTC)

        def _refresh(entry):
            entry.created_at = created_at
            entry.updated_at = None

        session.refresh.side_effect = _refresh
        user = SimpleNamespace(id="gm-1")

        result = create_campaign_map_config(
            "campaign-1",
            CampaignMapConfigCreate(
                mapName="  Dungeon Alpha  ",
                imageUrl="  /api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef  ",
                gridWidth=32,
                gridHeight=24,
                calibration={
                    "x": 0.1,
                    "y": 0.05,
                    "width": 0.8,
                    "height": 0.9,
                },
            ),
            user=user,
            session=session,
        )

        UUID(result.id)
        self.assertEqual(result.mapName, "Dungeon Alpha")
        self.assertEqual(
            result.imageUrl,
            "/api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef",
        )
        self.assertEqual(result.gridWidth, 32)
        self.assertEqual(result.gridHeight, 24)
        self.assertIsNotNone(result.calibration)
        self.assertEqual(result.createdAt, created_at)
        session.commit.assert_called_once()
        session.refresh.assert_called_once()
        mock_assert_managed_asset_exists.assert_called_once()

    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.assert_managed_asset_exists")
    @patch("app.api.routes.campaigns.require_gm")
    def test_update_campaign_map_config_replaces_previous_asset(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        mock_delete_managed_url,
    ):
        campaign = SimpleNamespace(id="campaign-1")
        entry = SimpleNamespace(
            id="map-1",
            campaign_id="campaign-1",
            name="Old Map",
            image_url="/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            grid_width=20,
            grid_height=14,
            calibration_x=0,
            calibration_y=0,
            calibration_width=1,
            calibration_height=1,
            blocked_cells_json=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        session.exec.return_value.first.return_value = entry

        result = update_campaign_map_config(
            "campaign-1",
            "map-1",
            CampaignMapConfigUpdate(
                mapName="Ruins",
                imageUrl="/api/assets/campaigns/campaign-1/maps/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                gridWidth=28,
                gridHeight=18,
                calibration={"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8},
            ),
            user=SimpleNamespace(id="gm-1"),
            session=session,
        )

        self.assertEqual(entry.name, "Ruins")
        self.assertEqual(
            entry.image_url,
            "/api/assets/campaigns/campaign-1/maps/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        self.assertEqual(result.id, "map-1")
        mock_assert_managed_asset_exists.assert_called_once()
        mock_delete_managed_url.assert_called_once_with(
            "/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.require_gm")
    def test_delete_campaign_map_config_removes_managed_asset(
        self,
        mock_require_gm,
        mock_delete_managed_url,
    ):
        campaign = SimpleNamespace(id="campaign-1")
        entry = SimpleNamespace(
            id="map-1",
            campaign_id="campaign-1",
            image_url="/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        session.exec.return_value.first.return_value = entry

        result = delete_campaign_map_config(
            "campaign-1",
            "map-1",
            user=SimpleNamespace(id="gm-1"),
            session=session,
        )

        self.assertIsNone(result)
        session.delete.assert_called_once_with(entry)
        session.commit.assert_called_once()
        mock_delete_managed_url.assert_called_once_with(
            "/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )

    def test_rejects_partial_grid_dimensions(self):
        with self.assertRaises(ValidationError):
            CampaignMapConfigUpdate(gridWidth=24)

    def test_rejects_calibration_outside_image_bounds(self):
        with self.assertRaises(ValidationError):
            CampaignMapConfigUpdate(
                calibration={
                    "x": 0.4,
                    "y": 0.1,
                    "width": 0.7,
                    "height": 0.9,
                }
            )

    def test_rejects_external_map_image_url(self):
        with self.assertRaises(ValidationError):
            CampaignMapConfigUpdate(imageUrl="https://cdn.example.com/dungeon.png")

    def test_rejects_empty_map_payload(self):
        with self.assertRaises(ValidationError):
            CampaignMapConfigCreate()

    # ------------------------------------------------------------------
    # Phase 1: blocked cells persistence
    # ------------------------------------------------------------------

    def test_encode_decode_blocked_cells_roundtrip(self):
        cells = [BlockedCell(x=3, y=5), BlockedCell(x=10, y=2)]
        encoded = encode_blocked_cells(cells)
        self.assertIsNotNone(encoded)
        decoded = decode_blocked_cells(encoded)
        self.assertEqual(len(decoded), 2)
        self.assertEqual(decoded[0].x, 3)
        self.assertEqual(decoded[0].y, 5)
        self.assertEqual(decoded[1].x, 10)
        self.assertEqual(decoded[1].y, 2)

    def test_encode_empty_blocked_cells_returns_none(self):
        self.assertIsNone(encode_blocked_cells([]))
        self.assertIsNone(encode_blocked_cells(None))

    def test_decode_none_returns_empty_list(self):
        self.assertEqual(decode_blocked_cells(None), [])

    def test_decode_invalid_json_returns_empty_list(self):
        self.assertEqual(decode_blocked_cells("not-json"), [])

    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.assert_managed_asset_exists")
    @patch("app.api.routes.campaigns.require_gm")
    def test_create_campaign_map_config_persists_blocked_cells(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        _mock_delete_managed_url,
    ):
        """blockedCells provided at create time are serialised to blocked_cells_json."""
        campaign = SimpleNamespace(id="campaign-1")
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        created_at = datetime.now(UTC)

        def _refresh(entry):
            entry.created_at = created_at
            entry.updated_at = None

        session.refresh.side_effect = _refresh
        user = SimpleNamespace(id="gm-1")
        captured_entry: list = []

        def _add(entry):
            captured_entry.append(entry)

        session.add.side_effect = _add

        create_campaign_map_config(
            "campaign-1",
            CampaignMapConfigCreate(
                imageUrl="/api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef",
                gridWidth=20,
                gridHeight=14,
                blockedCells=[{"x": 5, "y": 3}, {"x": 6, "y": 3}],
            ),
            user=user,
            session=session,
        )

        self.assertTrue(captured_entry)
        entry = captured_entry[0]
        self.assertIsNotNone(entry.blocked_cells_json)
        decoded = decode_blocked_cells(entry.blocked_cells_json)
        coords = {(c.x, c.y) for c in decoded}
        self.assertIn((5, 3), coords)
        self.assertIn((6, 3), coords)

    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.assert_managed_asset_exists")
    @patch("app.api.routes.campaigns.require_gm")
    def test_update_campaign_map_config_clears_blocked_cells_when_empty_list(
        self,
        mock_require_gm,
        _mock_assert_managed_asset_exists,
        _mock_delete_managed_url,
    ):
        """Passing blockedCells=[] in update must clear previously stored cells."""
        campaign = SimpleNamespace(id="campaign-1")
        entry = SimpleNamespace(
            id="map-1",
            campaign_id="campaign-1",
            name="Dungeon",
            image_url="/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            grid_width=20,
            grid_height=14,
            calibration_x=None,
            calibration_y=None,
            calibration_width=None,
            calibration_height=None,
            blocked_cells_json=encode_blocked_cells([BlockedCell(x=1, y=2)]),
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        session.exec.return_value.first.return_value = entry

        result = update_campaign_map_config(
            "campaign-1",
            "map-1",
            CampaignMapConfigUpdate(
                mapName="Dungeon",
                blockedCells=[],  # explicit clear
            ),
            user=SimpleNamespace(id="gm-1"),
            session=session,
        )

        # encode_blocked_cells([]) returns None → column is cleared
        self.assertIsNone(entry.blocked_cells_json)
        self.assertEqual(result.blockedCells, [])

    @patch("app.api.routes.campaigns.delete_managed_url_best_effort")
    @patch("app.api.routes.campaigns.assert_managed_asset_exists")
    @patch("app.api.routes.campaigns.require_gm")
    def test_update_campaign_map_config_leaves_blocked_cells_unchanged_when_omitted(
        self,
        mock_require_gm,
        _mock_assert_managed_asset_exists,
        _mock_delete_managed_url,
    ):
        """Omitting blockedCells from update payload must leave existing cells intact."""
        existing_json = encode_blocked_cells([BlockedCell(x=7, y=9)])
        entry = SimpleNamespace(
            id="map-1",
            campaign_id="campaign-1",
            name="Caves",
            image_url="/api/assets/campaigns/campaign-1/maps/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            grid_width=20,
            grid_height=14,
            calibration_x=None,
            calibration_y=None,
            calibration_width=None,
            calibration_height=None,
            blocked_cells_json=existing_json,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        mock_require_gm.return_value = (SimpleNamespace(id="campaign-1"), SimpleNamespace())
        session = MagicMock()
        session.exec.return_value.first.return_value = entry

        result = update_campaign_map_config(
            "campaign-1",
            "map-1",
            CampaignMapConfigUpdate(mapName="Caves Updated"),  # blockedCells not provided
            user=SimpleNamespace(id="gm-1"),
            session=session,
        )

        # The column should be untouched
        self.assertEqual(entry.blocked_cells_json, existing_json)
        self.assertEqual(len(result.blockedCells), 1)
        self.assertEqual(result.blockedCells[0].x, 7)
        self.assertEqual(result.blockedCells[0].y, 9)


if __name__ == "__main__":
    unittest.main()
