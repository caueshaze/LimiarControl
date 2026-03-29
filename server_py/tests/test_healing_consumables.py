import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.sessions.consumables import (
    _require_active_non_combat_session,
    use_session_healing_consumable,
)
from app.models.item import Item, ItemType
from app.models.session import SessionStatus
from app.models.session_state import SessionState
from app.schemas.session_consumable import SessionUseConsumableRequest
from app.services.goodberry_inventory import build_goodberry_expiration
from app.services.healing_consumables import (
    HealingConsumableError,
    apply_healing_outside_combat,
    resolve_healing_consumable,
    require_valid_healing_target,
    roll_healing_consumable,
)
from app.services.inventory_expiration import purge_expired_inventory_items


def _first_result(value):
    result = MagicMock()
    result.first.return_value = value
    return result


class HealingConsumableServiceTests(unittest.TestCase):
    def test_build_goodberry_expiration_adds_24_hours(self):
        created_at = datetime(2026, 3, 28, 12, 0, tzinfo=timezone.utc)
        expires_at = build_goodberry_expiration(created_at=created_at)

        self.assertEqual(expires_at - created_at, timedelta(hours=24))

    def test_roll_healing_consumable_rejects_wrong_manual_roll_count(self):
        item = Item(
            id="item-1",
            campaign_id="campaign-1",
            name="Healing Potion",
            type=ItemType.CONSUMABLE,
            description="Restores HP",
            heal_dice="2d4",
            heal_bonus=2,
        )

        with self.assertRaisesRegex(
            HealingConsumableError,
            "exactly 2 result",
        ):
            roll_healing_consumable(
                item,
                roll_source="manual",
                manual_rolls=[4],
            )

    def test_apply_healing_outside_combat_caps_hp(self):
        db = MagicMock()
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
        )
        target_state = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="user-2",
            state_json={"currentHP": 9, "maxHP": 12},
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

        with patch(
            "app.services.healing_consumables.get_actor_member",
            return_value=SimpleNamespace(display_name="Cleric"),
        ), patch(
            "app.services.healing_consumables._ensure_player_session_state",
            return_value=target_state,
        ):
            application = apply_healing_outside_combat(
                db,
                session_entry=session_entry,
                target_user_id="user-2",
                amount=8,
            )

        self.assertEqual(application.previous_hp, 9)
        self.assertEqual(application.new_hp, 12)
        self.assertEqual(application.max_hp, 12)
        self.assertEqual(target_state.state_json["currentHP"], 12)
        db.add.assert_called()

    def test_resolve_healing_consumable_rejects_expired_item(self):
        db = MagicMock()
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
        )
        actor_member = SimpleNamespace(id="member-1", user_id="user-1", display_name="Hero")
        inventory_item = SimpleNamespace(
            id="inv-1",
            campaign_id="campaign-123",
            party_id="party-123",
            member_id="member-1",
            item_id="item-1",
            quantity=1,
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.exec.side_effect = [
            _first_result(actor_member),
            _first_result(inventory_item),
        ]

        with self.assertRaisesRegex(HealingConsumableError, "expired"):
            resolve_healing_consumable(
                db,
                session_entry=session_entry,
                actor_user_id="user-1",
                inventory_item_id="inv-1",
            )

        db.delete.assert_called_once_with(inventory_item)
        db.flush.assert_called_once()

    def test_resolve_healing_consumable_accepts_unexpired_temporary_item(self):
        db = MagicMock()
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
        )
        actor_member = SimpleNamespace(id="member-1", user_id="user-1", display_name="Hero")
        inventory_item = SimpleNamespace(
            id="inv-1",
            campaign_id="campaign-123",
            party_id="party-123",
            member_id="member-1",
            item_id="item-1",
            quantity=3,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        item = Item(
            id="item-1",
            campaign_id="campaign-123",
            name="Goodberry",
            type=ItemType.CONSUMABLE,
            description="Restores 1 HP",
            heal_dice=None,
            heal_bonus=1,
        )
        db.exec.side_effect = [
            _first_result(actor_member),
            _first_result(inventory_item),
            _first_result(item),
        ]

        context = resolve_healing_consumable(
            db,
            session_entry=session_entry,
            actor_user_id="user-1",
            inventory_item_id="inv-1",
        )

        self.assertIs(context.inventory_item, inventory_item)
        self.assertEqual(context.item.name, "Goodberry")

    def test_require_valid_healing_target_rejects_target_outside_party(self):
        db = MagicMock()
        session_entry = SimpleNamespace(
            campaign_id="campaign-123",
            party_id="party-123",
        )
        db.exec.side_effect = [
            _first_result(SimpleNamespace(user_id="user-2", display_name="Cleric")),
            _first_result(None),
        ]

        with self.assertRaisesRegex(
            HealingConsumableError,
            "active party",
        ):
            require_valid_healing_target(
                db,
                session_entry=session_entry,
                actor_user_id="user-1",
                target_user_id="user-2",
            )


class InventoryExpirationServiceTests(unittest.TestCase):
    def test_purge_expired_inventory_items_removes_only_expired_entries(self):
        db = MagicMock()
        expired = SimpleNamespace(
            id="inv-expired",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
        fresh = SimpleNamespace(
            id="inv-fresh",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        result = MagicMock()
        result.all.return_value = [expired, fresh]
        db.exec.return_value = result

        removed_ids = purge_expired_inventory_items(
            db,
            campaign_id="campaign-123",
            member_id="member-1",
            now=datetime.now(timezone.utc),
        )

        self.assertEqual(removed_ids, ["inv-expired"])
        db.delete.assert_called_once_with(expired)
        db.flush.assert_called_once()


class SessionHealingConsumableRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_use_session_healing_consumable_for_self(self):
        session = MagicMock()
        user = SimpleNamespace(id="user-1")
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
            status=SessionStatus.ACTIVE,
        )
        context = SimpleNamespace(
            session_entry=session_entry,
            actor_member=SimpleNamespace(id="member-1", user_id="user-1", display_name="Hero"),
            inventory_item=SimpleNamespace(id="inv-1"),
            item=SimpleNamespace(id="item-1", name="Healing Potion"),
        )
        roll = SimpleNamespace(
            total_healing=7,
            effect_dice="2d4",
            effect_bonus=2,
            effect_rolls=[3, 2],
            roll_source="system",
            base_effect=5,
        )
        state_model = SessionState(
            id="state-1",
            session_id="session-123",
            player_user_id="user-1",
            state_json={"currentHP": 7, "maxHP": 12},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        application = SimpleNamespace(
            target_user_id="user-1",
            target_display_name="Hero",
            previous_hp=0,
            new_hp=7,
            max_hp=12,
            state_model=state_model,
        )

        with patch(
            "app.api.routes.sessions.consumables._require_active_non_combat_session",
            return_value=session_entry,
        ), patch(
            "app.api.routes.sessions.consumables.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.api.routes.sessions.consumables.require_valid_healing_target",
            return_value=SimpleNamespace(display_name="Hero"),
        ), patch(
            "app.api.routes.sessions.consumables.roll_healing_consumable",
            return_value=roll,
        ), patch(
            "app.api.routes.sessions.consumables.apply_healing_outside_combat",
            return_value=application,
        ), patch(
            "app.api.routes.sessions.consumables.consume_inventory_item",
            return_value=0,
        ), patch(
            "app.api.routes.sessions.consumables.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.api.routes.sessions.consumables.record_consumable_used_activity",
        ), patch(
            "app.api.routes.sessions.consumables.publish_state_update",
        ), patch(
            "app.api.routes.sessions.consumables.publish_consumable_used_realtime",
        ):
            result = await use_session_healing_consumable(
                "session-123",
                SessionUseConsumableRequest(
                    inventoryItemId="inv-1",
                    rollSource="system",
                ),
                user=user,
                session=session,
            )

        self.assertEqual(result.actorUserId, "user-1")
        self.assertEqual(result.targetPlayerUserId, "user-1")
        self.assertEqual(result.itemName, "Healing Potion")
        self.assertEqual(result.healingApplied, 7)
        self.assertEqual(result.newHp, 7)
        self.assertEqual(result.remainingQuantity, 0)
        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(state_model)

    async def test_use_session_healing_consumable_for_ally(self):
        session = MagicMock()
        user = SimpleNamespace(id="user-1")
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
            status=SessionStatus.ACTIVE,
        )
        context = SimpleNamespace(
            session_entry=session_entry,
            actor_member=SimpleNamespace(id="member-1", user_id="user-1", display_name="Hero"),
            inventory_item=SimpleNamespace(id="inv-1"),
            item=SimpleNamespace(id="item-1", name="Healing Potion"),
        )
        roll = SimpleNamespace(
            total_healing=9,
            effect_dice="2d4",
            effect_bonus=2,
            effect_rolls=[4, 3],
            roll_source="manual",
            base_effect=7,
        )
        state_model = SessionState(
            id="state-2",
            session_id="session-123",
            player_user_id="user-2",
            state_json={"currentHP": 11, "maxHP": 15},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        application = SimpleNamespace(
            target_user_id="user-2",
            target_display_name="Cleric",
            previous_hp=2,
            new_hp=11,
            max_hp=15,
            state_model=state_model,
        )

        with patch(
            "app.api.routes.sessions.consumables._require_active_non_combat_session",
            return_value=session_entry,
        ), patch(
            "app.api.routes.sessions.consumables.resolve_healing_consumable",
            return_value=context,
        ), patch(
            "app.api.routes.sessions.consumables.require_valid_healing_target",
            return_value=SimpleNamespace(display_name="Cleric"),
        ), patch(
            "app.api.routes.sessions.consumables.roll_healing_consumable",
            return_value=roll,
        ), patch(
            "app.api.routes.sessions.consumables.apply_healing_outside_combat",
            return_value=application,
        ) as mock_apply, patch(
            "app.api.routes.sessions.consumables.consume_inventory_item",
            return_value=1,
        ), patch(
            "app.api.routes.sessions.consumables.build_consumable_used_payload",
            return_value={"type": "consumable_used"},
        ), patch(
            "app.api.routes.sessions.consumables.record_consumable_used_activity",
        ), patch(
            "app.api.routes.sessions.consumables.publish_state_update",
        ), patch(
            "app.api.routes.sessions.consumables.publish_consumable_used_realtime",
        ):
            result = await use_session_healing_consumable(
                "session-123",
                SessionUseConsumableRequest(
                    inventoryItemId="inv-1",
                    targetPlayerUserId="user-2",
                    rollSource="manual",
                    manualRolls=[4, 3],
                ),
                user=user,
                session=session,
            )

        self.assertEqual(result.targetPlayerUserId, "user-2")
        self.assertEqual(result.targetDisplayName, "Cleric")
        self.assertEqual(result.healingApplied, 9)
        self.assertEqual(result.effectRollSource, "manual")
        mock_apply.assert_called_once_with(
            session,
            session_entry=session_entry,
            target_user_id="user-2",
            amount=9,
        )

    async def test_use_session_healing_consumable_rejects_non_healing_item(self):
        session = MagicMock()
        user = SimpleNamespace(id="user-1")
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
            status=SessionStatus.ACTIVE,
        )

        with patch(
            "app.api.routes.sessions.consumables._require_active_non_combat_session",
            return_value=session_entry,
        ), patch(
            "app.api.routes.sessions.consumables.resolve_healing_consumable",
            side_effect=HealingConsumableError(
                "Consumable has no structured healing effect",
                400,
            ),
        ):
            with self.assertRaises(HTTPException) as ctx:
                await use_session_healing_consumable(
                    "session-123",
                    SessionUseConsumableRequest(
                        inventoryItemId="inv-1",
                        rollSource="system",
                    ),
                    user=user,
                    session=session,
                )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("structured healing effect", ctx.exception.detail)

    def test_require_active_non_combat_session_rejects_active_combat(self):
        session = MagicMock()
        session_entry = SimpleNamespace(
            id="session-123",
            campaign_id="campaign-123",
            party_id="party-123",
            status=SessionStatus.ACTIVE,
        )

        with patch(
            "app.api.routes.sessions.consumables.get_session_entry",
            return_value=session_entry,
        ), patch(
            "app.api.routes.sessions.consumables.get_or_create_session_runtime",
            return_value=SimpleNamespace(combat_active=True),
        ):
            with self.assertRaises(HTTPException) as ctx:
                _require_active_non_combat_session("session-123", session)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("unavailable during combat", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
