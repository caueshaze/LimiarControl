from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.routes.sessions.shop.service import (
    add_inventory_item_condition_tag_service,
    remove_inventory_item_condition_tag_service,
)
from app.models.campaign import RoleMode


class TestInventoryConditionTagsService(unittest.IsolatedAsyncioTestCase):
    def _session_entry(self):
        return SimpleNamespace(
            id="s1",
            campaign_id="c1",
            party_id="p1",
        )

    def _member(self, *, gm: bool = False):
        return SimpleNamespace(
            id="m1",
            role_mode=RoleMode.GM if gm else RoleMode.PLAYER,
            display_name="Tester",
        )

    def _inventory_item(self):
        return SimpleNamespace(
            id="inv1",
            campaign_id="c1",
            party_id="p1",
            member_id="m1",
            item_id="i1",
            condition_tags=[],
            quantity=1,
            charges_current=None,
            is_equipped=False,
            notes=None,
            source_spell_canonical_key=None,
            expires_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

    async def test_add_is_idempotent_without_spam(self):
        session = MagicMock()
        user = SimpleNamespace(id="u1")
        inventory_item = self._inventory_item()
        item = SimpleNamespace(id="i1", name="Espada")
        session.exec.return_value.first.side_effect = [inventory_item, item, inventory_item, item]

        with (
            patch("app.api.routes.sessions.shop.service.require_active_shop_session", return_value=(self._session_entry(), object())),
            patch("app.api.routes.sessions.shop.service._require_inventory_access", return_value=self._member(gm=True)),
        ):
            result = await add_inventory_item_condition_tag_service("s1", "inv1", SimpleNamespace(tag="broken"), user, session)
            self.assertEqual(inventory_item.condition_tags, ["broken"])
            self.assertEqual(result.conditionTags, ["broken"])
            self.assertEqual(result.conditionTagLabels, [{"tag": "broken", "label": "Quebrado"}])
            await add_inventory_item_condition_tag_service("s1", "inv1", SimpleNamespace(tag="broken"), user, session)
            self.assertEqual(inventory_item.condition_tags, ["broken"])

    async def test_remove_is_idempotent(self):
        session = MagicMock()
        user = SimpleNamespace(id="u1")
        inventory_item = self._inventory_item()
        inventory_item.condition_tags = ["broken"]
        item = SimpleNamespace(id="i1", name="Espada")
        session.exec.return_value.first.side_effect = [inventory_item, item, inventory_item, item]

        with (
            patch("app.api.routes.sessions.shop.service.require_active_shop_session", return_value=(self._session_entry(), object())),
            patch("app.api.routes.sessions.shop.service._require_inventory_access", return_value=self._member(gm=True)),
        ):
            await remove_inventory_item_condition_tag_service("s1", "inv1", "broken", user, session)
            self.assertEqual(inventory_item.condition_tags, [])
            await remove_inventory_item_condition_tag_service("s1", "inv1", "broken", user, session)
            self.assertEqual(inventory_item.condition_tags, [])

    async def test_invalid_tag_400(self):
        session = MagicMock()
        user = SimpleNamespace(id="u1")
        inventory_item = self._inventory_item()
        session.exec.return_value.first.return_value = inventory_item
        with (
            patch("app.api.routes.sessions.shop.service.require_active_shop_session", return_value=(self._session_entry(), object())),
            patch("app.api.routes.sessions.shop.service._require_inventory_access", return_value=self._member(gm=True)),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await add_inventory_item_condition_tag_service("s1", "inv1", SimpleNamespace(tag="BROKEN"), user, session)
            self.assertEqual(ctx.exception.status_code, 400)
