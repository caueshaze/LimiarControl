import unittest
from asyncio import run
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes.party_common import broadcast_party_member_updated_safe
from app.api.routes.party_listing_service import add_party_member_service
from app.api.routes.party_membership_service import (
    decline_party_invite_service,
    join_party_invite_service,
    leave_party_service,
)
from app.models.campaign import RoleMode
from app.models.party_member import PartyMemberStatus


class PartyRealtimeResilienceTests(unittest.TestCase):
    def test_broadcast_party_member_updated_safe_ignores_publish_failure(self):
        with patch(
            "app.api.routes.party_common.broadcast_party_member_updated",
            new=AsyncMock(side_effect=RuntimeError("publish failed")),
        ):
            run(
                broadcast_party_member_updated_safe(
                    "campaign-1",
                    "party-1",
                    "player-1",
                    RoleMode.PLAYER,
                    PartyMemberStatus.INVITED,
                )
            )

    def test_add_party_member_service_returns_member_after_commit(self):
        session = MagicMock()
        created_at = datetime(2026, 3, 30, 20, 0, tzinfo=timezone.utc)
        entry = SimpleNamespace(
            user_id="player-1",
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.INVITED,
            created_at=created_at,
        )
        session.refresh.side_effect = lambda obj: None

        with patch(
            "app.api.routes.party_listing_service.user_id",
            return_value="gm-1",
        ), patch(
            "app.api.routes.party_listing_service.get_party_or_404",
            return_value=SimpleNamespace(campaign_id="campaign-1", gm_user_id="gm-1"),
        ), patch(
            "app.api.routes.party_listing_service.ensure_campaign_player_member",
        ), patch(
            "app.api.routes.party_listing_service.get_party_member",
            return_value=None,
        ), patch(
            "app.api.routes.party_listing_service.PartyMember",
            return_value=entry,
        ), patch(
            "app.api.routes.party_listing_service.broadcast_party_member_updated_safe",
            new=AsyncMock(),
        ):
            result = run(
                add_party_member_service(
                    "party-1",
                    SimpleNamespace(
                        userId="player-1",
                        role=RoleMode.PLAYER,
                        status=PartyMemberStatus.INVITED,
                    ),
                    user=SimpleNamespace(id="gm-1"),
                    session=session,
                )
            )

        session.commit.assert_called_once_with()
        self.assertEqual(result.userId, "player-1")
        self.assertEqual(result.status, PartyMemberStatus.INVITED)
        self.assertEqual(result.createdAt, created_at)

    def test_join_party_invite_service_ignores_realtime_publish_failure(self):
        session = MagicMock()
        created_at = datetime(2026, 3, 30, 20, 5, tzinfo=timezone.utc)
        member = SimpleNamespace(
            user_id="player-1",
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.INVITED,
            created_at=created_at,
        )

        with patch(
            "app.api.routes.party_membership_service.get_party_or_404",
            return_value=SimpleNamespace(campaign_id="campaign-1"),
        ), patch(
            "app.api.routes.party_membership_service.user_id",
            return_value="player-1",
        ), patch(
            "app.api.routes.party_membership_service.get_party_member_or_404",
            return_value=member,
        ), patch(
            "app.api.routes.party_membership_service.broadcast_party_member_updated_safe",
            new=AsyncMock(),
        ):
            result = run(
                join_party_invite_service(
                    "party-1",
                    user=SimpleNamespace(id="player-1"),
                    session=session,
                )
            )

        session.commit.assert_called_once_with()
        self.assertEqual(member.status, PartyMemberStatus.JOINED)
        self.assertEqual(result.status, PartyMemberStatus.JOINED)
        self.assertEqual(result.createdAt, created_at)

    def test_decline_party_invite_service_ignores_realtime_publish_failure(self):
        session = MagicMock()
        created_at = datetime(2026, 3, 30, 20, 10, tzinfo=timezone.utc)
        member = SimpleNamespace(
            user_id="player-1",
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.INVITED,
            created_at=created_at,
        )

        with patch(
            "app.api.routes.party_membership_service.get_party_or_404",
            return_value=SimpleNamespace(campaign_id="campaign-1"),
        ), patch(
            "app.api.routes.party_membership_service.user_id",
            return_value="player-1",
        ), patch(
            "app.api.routes.party_membership_service.get_party_member_or_404",
            return_value=member,
        ), patch(
            "app.api.routes.party_membership_service.broadcast_party_member_updated_safe",
            new=AsyncMock(),
        ):
            result = run(
                decline_party_invite_service(
                    "party-1",
                    user=SimpleNamespace(id="player-1"),
                    session=session,
                )
            )

        session.commit.assert_called_once_with()
        self.assertEqual(member.status, PartyMemberStatus.DECLINED)
        self.assertEqual(result.status, PartyMemberStatus.DECLINED)
        self.assertEqual(result.createdAt, created_at)

    def test_leave_party_service_ignores_realtime_publish_failure(self):
        session = MagicMock()
        created_at = datetime(2026, 3, 30, 20, 15, tzinfo=timezone.utc)
        member = SimpleNamespace(
            user_id="player-1",
            role=RoleMode.PLAYER,
            status=PartyMemberStatus.JOINED,
            created_at=created_at,
        )

        with patch(
            "app.api.routes.party_membership_service.get_party_or_404",
            return_value=SimpleNamespace(campaign_id="campaign-1"),
        ), patch(
            "app.api.routes.party_membership_service.user_id",
            return_value="player-1",
        ), patch(
            "app.api.routes.party_membership_service.get_party_member_or_404",
            return_value=member,
        ), patch(
            "app.api.routes.party_membership_service.broadcast_party_member_updated_safe",
            new=AsyncMock(),
        ):
            result = run(
                leave_party_service(
                    "party-1",
                    user=SimpleNamespace(id="player-1"),
                    session=session,
                )
            )

        session.commit.assert_called_once_with()
        self.assertEqual(member.status, PartyMemberStatus.LEFT)
        self.assertEqual(result.status, PartyMemberStatus.LEFT)
        self.assertEqual(result.createdAt, created_at)


if __name__ == "__main__":
    unittest.main()
