import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

from fastapi import HTTPException
from pydantic import ValidationError

from app.api.routes.campaign_entities import create_campaign_entity, update_campaign_entity
from app.schemas.campaign_entity import CampaignEntityCreate, CampaignEntityUpdate


class CampaignEntityMediaTests(unittest.TestCase):
    def test_rejects_external_entity_image_url(self):
        with self.assertRaises(ValidationError):
            CampaignEntityCreate(name="Goblin", imageUrl="https://cdn.example.com/goblin.png")

    @patch("app.api.routes.campaign_entities.delete_managed_url_best_effort")
    @patch("app.api.routes.campaign_entities.copy_object")
    @patch("app.api.routes.campaign_entities.assert_managed_asset_exists")
    @patch("app.api.routes.campaign_entities.require_gm")
    def test_create_promotes_temporary_entity_image(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        mock_copy_object,
        mock_delete_managed_url,
    ):
        mock_require_gm.return_value = (SimpleNamespace(id="campaign-1"), SimpleNamespace())
        session = MagicMock()
        session.refresh.side_effect = lambda entry: setattr(entry, "created_at", datetime.now(UTC))
        user = SimpleNamespace(id="gm-1")

        result = create_campaign_entity(
            "campaign-1",
            CampaignEntityCreate(
                name="Goblin",
                imageUrl="/api/assets/campaigns/campaign-1/entities/tmp/1234567890abcdef1234567890abcdef",
            ),
            user=user,
            session=session,
        )

        self.assertEqual(
            result.imageUrl,
            "/api/assets/campaigns/campaign-1/entities/"
            f"{result.id}/1234567890abcdef1234567890abcdef",
        )
        mock_assert_managed_asset_exists.assert_called_once()
        mock_copy_object.assert_called_once()
        mock_delete_managed_url.assert_called_once_with(
            "/api/assets/campaigns/campaign-1/entities/tmp/1234567890abcdef1234567890abcdef"
        )
        session.commit.assert_called_once()

    @patch("app.api.routes.campaign_entities.delete_managed_url_best_effort")
    @patch("app.api.routes.campaign_entities.copy_object")
    @patch("app.api.routes.campaign_entities.assert_managed_asset_exists")
    @patch("app.api.routes.campaign_entities.require_gm")
    def test_update_replaces_previous_image_after_commit(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        mock_copy_object,
        mock_delete_managed_url,
    ):
        mock_require_gm.return_value = (SimpleNamespace(id="campaign-1"), SimpleNamespace())
        entry = SimpleNamespace(
            id="entity-1",
            campaign_id="campaign-1",
            name="Goblin",
            category="enemy",
            size=None,
            creature_type=None,
            creature_subtype=None,
            description=None,
            image_url="/api/assets/campaigns/campaign-1/entities/entity-1/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            armor_class=None,
            max_hp=None,
            speed_meters=None,
            initiative_bonus=None,
            abilities=None,
            saving_throws=None,
            skills=None,
            senses=None,
            spellcasting=None,
            damage_resistances=None,
            damage_immunities=None,
            damage_vulnerabilities=None,
            condition_immunities=None,
            combat_actions=None,
            actions=None,
            notes_private=None,
            notes_public=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        session = MagicMock()
        session.exec.return_value.first.return_value = entry
        user = SimpleNamespace(id="gm-1")

        result = update_campaign_entity(
            "campaign-1",
            "entity-1",
            CampaignEntityUpdate(
                name="Goblin",
                imageUrl="/api/assets/campaigns/campaign-1/entities/tmp/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            ),
            user=user,
            session=session,
        )

        self.assertEqual(
            result.imageUrl,
            "/api/assets/campaigns/campaign-1/entities/entity-1/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )
        mock_assert_managed_asset_exists.assert_called_once()
        mock_copy_object.assert_called_once()
        self.assertEqual(
            mock_delete_managed_url.mock_calls,
            [
                call("/api/assets/campaigns/campaign-1/entities/tmp/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"),
                call("/api/assets/campaigns/campaign-1/entities/entity-1/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"),
            ],
        )

    @patch("app.api.routes.campaign_entities.delete_managed_url_best_effort")
    @patch("app.api.routes.campaign_entities.copy_object")
    @patch("app.api.routes.campaign_entities.assert_managed_asset_exists")
    @patch("app.api.routes.campaign_entities.require_gm")
    def test_update_rejects_final_image_for_another_entity(
        self,
        mock_require_gm,
        mock_assert_managed_asset_exists,
        _mock_copy_object,
        _mock_delete_managed_url,
    ):
        mock_require_gm.return_value = (SimpleNamespace(id="campaign-1"), SimpleNamespace())
        entry = SimpleNamespace(
            id="entity-1",
            campaign_id="campaign-1",
            name="Goblin",
            category="enemy",
            size=None,
            creature_type=None,
            creature_subtype=None,
            description=None,
            image_url=None,
            armor_class=None,
            max_hp=None,
            speed_meters=None,
            initiative_bonus=None,
            abilities=None,
            saving_throws=None,
            skills=None,
            senses=None,
            spellcasting=None,
            damage_resistances=None,
            damage_immunities=None,
            damage_vulnerabilities=None,
            condition_immunities=None,
            combat_actions=None,
            actions=None,
            notes_private=None,
            notes_public=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
        session = MagicMock()
        session.exec.return_value.first.return_value = entry

        with self.assertRaises(HTTPException) as ctx:
            update_campaign_entity(
                "campaign-1",
                "entity-1",
                CampaignEntityUpdate(
                    name="Goblin",
                    imageUrl="/api/assets/campaigns/campaign-1/entities/entity-2/cccccccccccccccccccccccccccccccc",
                ),
                user=SimpleNamespace(id="gm-1"),
                session=session,
            )

        self.assertEqual(ctx.exception.status_code, 400)
        mock_assert_managed_asset_exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
