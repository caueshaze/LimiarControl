import unittest

from app.services.media_storage_service import ManagedAssetRef, parse_managed_url


class ManagedAssetUrlTests(unittest.TestCase):
    def test_parse_campaign_map_url(self):
        ref = parse_managed_url(
            "/api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef"
        )
        self.assertEqual(
            ref,
            ManagedAssetRef(
                kind="campaign_map",
                campaign_id="campaign-1",
                asset_id="1234567890abcdef1234567890abcdef",
            ),
        )

    def test_parse_entity_urls(self):
        temp_ref = parse_managed_url(
            "/api/assets/campaigns/campaign-1/entities/tmp/1234567890abcdef1234567890abcdef"
        )
        final_ref = parse_managed_url(
            "/api/assets/campaigns/campaign-1/entities/entity-1/1234567890abcdef1234567890abcdef"
        )
        self.assertEqual(temp_ref.kind, "entity_temp")
        self.assertEqual(final_ref.kind, "entity_final")
        self.assertEqual(final_ref.entity_id, "entity-1")

    def test_rejects_non_canonical_values(self):
        with self.assertRaises(ValueError):
            parse_managed_url(
                "/api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef?x=1"
            )
        with self.assertRaises(ValueError):
            parse_managed_url(" /api/assets/campaigns/campaign-1/maps/1234567890abcdef1234567890abcdef ")
        with self.assertRaises(ValueError):
            parse_managed_url("/api/assets/campaigns/campaign-1/maps/not-a-managed-id")


if __name__ == "__main__":
    unittest.main()
