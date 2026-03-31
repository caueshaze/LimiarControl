import unittest
from datetime import datetime, UTC
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.campaigns import (
    _ensure_unique_campaign_name_for_gm,
    create_campaign,
    update_campaign,
)
from app.models.campaign import SystemType
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CampaignNameUniquenessTests(unittest.TestCase):
    def test_rejects_duplicate_name_for_same_gm(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = "campaign-1"

        with self.assertRaises(HTTPException) as ctx:
            _ensure_unique_campaign_name_for_gm("Mesa Teste", "gm-1", session)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "You already have a campaign with this name")

    def test_allows_same_name_when_updating_same_campaign(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        _ensure_unique_campaign_name_for_gm(
            "Mesa Teste",
            "gm-1",
            session,
            exclude_campaign_id="campaign-1",
        )

        session.exec.assert_called_once()

    @patch("app.api.routes.campaigns.snapshot_campaign_spells")
    @patch("app.api.routes.campaigns.snapshot_campaign_catalog")
    @patch("app.api.routes.campaigns._ensure_unique_campaign_name_for_gm")
    def test_create_campaign_enforces_name_uniqueness(
        self,
        mock_unique_name,
        _mock_snapshot_catalog,
        _mock_snapshot_spells,
    ):
        session = MagicMock()
        session.flush.return_value = None
        session.commit.return_value = None
        user = SimpleNamespace(id="gm-1", username="gm", display_name="GM")

        def refresh_campaign(campaign):
            campaign.created_at = datetime.now(UTC)
            campaign.updated_at = None

        session.refresh.side_effect = refresh_campaign

        create_campaign(
            CampaignCreate(name="  Mesa Teste  ", system=SystemType.DND5E),
            user=user,
            session=session,
        )

        mock_unique_name.assert_called_once_with("Mesa Teste", "gm-1", session)

    @patch("app.api.routes.campaigns.require_gm")
    @patch("app.api.routes.campaigns._ensure_unique_campaign_name_for_gm")
    def test_update_campaign_enforces_name_uniqueness(
        self,
        mock_unique_name,
        mock_require_gm,
    ):
        campaign = SimpleNamespace(
            id="campaign-1",
            name="Mesa Antiga",
            system=SystemType.DND5E,
            role_mode="GM",
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()
        user = SimpleNamespace(id="gm-1")

        update_campaign(
            "campaign-1",
            CampaignUpdate(name="  Mesa Teste  "),
            user=user,
            session=session,
        )

        mock_unique_name.assert_called_once_with(
            "Mesa Teste",
            "gm-1",
            session,
            exclude_campaign_id="campaign-1",
        )


if __name__ == "__main__":
    unittest.main()
