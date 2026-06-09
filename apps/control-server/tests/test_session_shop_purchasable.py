from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.sessions.shop.service import (
    buy_session_shop_item_service,
    list_session_shop_items_service,
)
from app.models.item import Item, ItemType
from app.schemas.inventory import InventoryBuy


class SessionShopPurchasableTests(unittest.IsolatedAsyncioTestCase):
    def _item(self, *, item_id: str, is_purchasable: bool) -> Item:
        return Item(
            id=item_id,
            campaign_id="camp-1",
            name=f"Item {item_id}",
            type=ItemType.MISC,
            description="Test item",
            is_purchasable=is_purchasable,
            created_at=datetime.now(timezone.utc),
        )

    def test_list_session_shop_items_filters_non_purchasable_items(self):
        session = MagicMock()
        purchasable_item = self._item(item_id="item-1", is_purchasable=True)
        hidden_item = self._item(item_id="item-2", is_purchasable=False)
        session.exec.return_value.all.return_value = [purchasable_item]

        with (
            patch(
                "app.api.routes.sessions.shop.service.require_active_shop_session",
                return_value=(SimpleNamespace(campaign_id="camp-1"), object()),
            ),
            patch(
                "app.api.routes.sessions.shop.service.require_campaign_member",
                return_value=SimpleNamespace(id="member-1"),
            ),
        ):
            result = list_session_shop_items_service("session-1", SimpleNamespace(id="user-1"), session)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, "item-1")
        self.assertNotEqual(result[0].id, hidden_item.id)

    async def test_buy_session_shop_item_rejects_non_purchasable_item(self):
        session = MagicMock()
        session.exec.return_value.first.return_value = self._item(
            item_id="item-hidden",
            is_purchasable=False,
        )
        payload = InventoryBuy(itemId="item-hidden", quantity=1)

        with (
            patch(
                "app.api.routes.sessions.shop.service.require_active_shop_session",
                return_value=(
                    SimpleNamespace(campaign_id="camp-1", status="ACTIVE"),
                    SimpleNamespace(shop_open=True),
                ),
            ),
            patch(
                "app.api.routes.sessions.shop.service.require_campaign_member",
                return_value=SimpleNamespace(
                    id="member-1",
                    role_mode="PLAYER",
                    display_name="Lia",
                ),
            ),
            patch("app.api.routes.sessions.shop.service.ensure_shop_open"),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await buy_session_shop_item_service(
                    "session-1",
                    payload,
                    SimpleNamespace(id="user-1"),
                    session,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Item is not available in the shop")


if __name__ == "__main__":
    unittest.main()
