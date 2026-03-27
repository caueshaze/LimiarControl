import unittest
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock, patch

from fastapi import HTTPException

from app.api.routes.campaigns import delete_campaign
from app.api.routes.parties import delete_party


class CampaignDeletionRouteTests(unittest.TestCase):
    @patch("app.api.routes.campaigns.delete_campaign_tree")
    @patch("app.api.routes.campaigns.require_gm")
    def test_delete_campaign_uses_cleanup_service(self, mock_require_gm, mock_delete_tree):
        campaign = SimpleNamespace(id="campaign-1")
        mock_require_gm.return_value = (campaign, SimpleNamespace())
        session = MagicMock()

        result = delete_campaign("campaign-1", user=SimpleNamespace(), session=session)

        self.assertIsNone(result)
        mock_require_gm.assert_called_once()
        mock_delete_tree.assert_called_once_with(session, campaign)
        session.commit.assert_called_once_with()


class PartyDeletionRouteTests(unittest.TestCase):
    @patch("app.api.routes.parties.delete_party_tree")
    @patch("app.api.routes.parties.user_id")
    @patch("app.api.routes.parties.require_gm")
    @patch("app.api.routes.parties.get_party_or_404")
    def test_delete_party_rejects_non_owner_gm(
        self,
        mock_get_party,
        mock_require_gm,
        mock_user_id,
        mock_delete_tree,
    ):
        mock_get_party.return_value = SimpleNamespace(
            id="party-1",
            campaign_id="campaign-1",
            gm_user_id="gm-owner",
        )
        mock_user_id.return_value = "gm-other"
        session = MagicMock()

        with self.assertRaises(HTTPException) as ctx:
            delete_party("party-1", user=SimpleNamespace(), session=session)

        self.assertEqual(ctx.exception.status_code, 403)
        mock_require_gm.assert_called_once()
        mock_delete_tree.assert_not_called()
        session.commit.assert_not_called()

    @patch("app.api.routes.parties.delete_party_tree")
    @patch("app.api.routes.parties.user_id")
    @patch("app.api.routes.parties.require_gm")
    @patch("app.api.routes.parties.get_party_or_404")
    def test_delete_party_uses_cleanup_service(
        self,
        mock_get_party,
        mock_require_gm,
        mock_user_id,
        mock_delete_tree,
    ):
        party = SimpleNamespace(
            id="party-1",
            campaign_id="campaign-1",
            gm_user_id="gm-owner",
        )
        mock_get_party.return_value = party
        mock_user_id.return_value = "gm-owner"
        session = MagicMock()

        result = delete_party("party-1", user=SimpleNamespace(), session=session)

        self.assertIsNone(result)
        mock_require_gm.assert_called_once_with("campaign-1", ANY, session)
        mock_delete_tree.assert_called_once_with(session, party)
        session.commit.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
