import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.party_listing_service import (
    create_party_service,
    ensure_unique_party_name_for_gm,
)
from app.schemas.party import PartyCreate


class PartyNameUniquenessTests(unittest.TestCase):
    def test_rejects_duplicate_name_for_same_gm(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = "party-1"

        with self.assertRaises(HTTPException) as ctx:
            ensure_unique_party_name_for_gm("Mesa Principal", "gm-1", session)

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail, "You already have a party with this name")

    @patch("app.api.routes.party_listing_service.ensure_unique_party_name_for_gm")
    def test_create_party_enforces_name_uniqueness(self, mock_unique_name):
        session = MagicMock()
        session.get.return_value = SimpleNamespace(id="campaign-1")
        user = SimpleNamespace(id="gm-1")

        create_party_service(
          PartyCreate(campaignId="campaign-1", name="  Mesa Principal  ", playerIds=[]),
          user,
          session,
        )

        mock_unique_name.assert_called_once_with("Mesa Principal", "gm-1", session)


if __name__ == "__main__":
    unittest.main()
