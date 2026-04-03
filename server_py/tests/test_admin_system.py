import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes.admin_system import (
    admin_delete_user,
    admin_delete_campaign,
    admin_diagnostics,
    admin_list_campaigns,
    admin_list_users,
    admin_overview,
    admin_update_user,
)
from app.models.campaign import RoleMode, SystemType
from app.schemas.admin_system import (
    AdminCampaignRead,
    AdminDiagnosticsRead,
    AdminOverviewRead,
    AdminUserRead,
    AdminUserUpdate,
)
from app.services.admin_system import delete_admin_user, get_admin_diagnostics
from app.services.admin_system import update_admin_user as update_admin_user_service


class AdminSystemServiceTests(unittest.TestCase):
    @patch("app.services.admin_system.delete_campaign_tree")
    def test_delete_admin_user_deletes_sole_gm_campaign_and_user(
        self,
        mock_delete_campaign_tree,
    ):
        user = SimpleNamespace(
            id="user-1",
            username="root",
            display_name="Root",
            role=RoleMode.GM,
            is_system_admin=True,
        )
        campaign = SimpleNamespace(id="campaign-1")

        gm_campaigns_result = MagicMock()
        gm_campaigns_result.all.return_value = ["campaign-1"]
        other_gm_result = MagicMock()
        other_gm_result.first.return_value = None
        parties_result = MagicMock()
        parties_result.all.return_value = []
        member_ids_result = MagicMock()
        member_ids_result.all.return_value = ["member-1"]

        session = MagicMock()
        session.get.return_value = campaign
        session.exec.side_effect = [
            gm_campaigns_result,
            other_gm_result,
            parties_result,
            member_ids_result,
            *[MagicMock() for _ in range(13)],
        ]

        with patch("app.services.admin_system.get_admin_user_by_id", return_value=user):
            delete_admin_user(db=session, user_id="user-1")

        mock_delete_campaign_tree.assert_called_once_with(session, campaign)
        session.delete.assert_called_once_with(user)
        session.commit.assert_called_once()

    def test_get_admin_diagnostics_uses_session_exec_for_health_check(self):
        health_result = MagicMock()
        health_result.one.return_value = 1
        count_results = []
        for value in [10, 4, 5, 8, 2, 1]:
            result = MagicMock()
            result.one.return_value = value
            count_results.append(result)

        session = MagicMock()
        session.exec.side_effect = [health_result, *count_results]

        diagnostics = get_admin_diagnostics(db=session)

        self.assertTrue(diagnostics.databaseOk)
        self.assertEqual(diagnostics.databaseMessage, "ok")
        self.assertEqual(diagnostics.usersTotal, 10)
        self.assertEqual(diagnostics.activeCombatsTotal, 1)
        session.get_bind.assert_not_called()

    def test_update_admin_user_allows_demoting_last_system_admin(self):
        user = SimpleNamespace(
            id="user-1",
            username="root",
            display_name="Root",
            role=RoleMode.GM,
            is_system_admin=True,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

        first_result = MagicMock()
        first_result.first.return_value = user
        campaigns_result = MagicMock()
        campaigns_result.one.return_value = 2
        gm_campaigns_result = MagicMock()
        gm_campaigns_result.one.return_value = 1
        parties_result = MagicMock()
        parties_result.one.return_value = 0

        session = MagicMock()
        session.exec.side_effect = [
            first_result,
            campaigns_result,
            gm_campaigns_result,
            parties_result,
        ]

        result = update_admin_user_service(
            db=session,
            user_id="user-1",
            payload=AdminUserUpdate(isSystemAdmin=False),
        )

        self.assertFalse(result.isSystemAdmin)
        session.commit.assert_called_once()

    def test_update_admin_user_updates_role_and_admin_flag(self):
        user = SimpleNamespace(
            id="user-1",
            username="gm",
            display_name=None,
            role=RoleMode.GM,
            is_system_admin=True,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
        )

        first_result = MagicMock()
        first_result.first.return_value = user
        count_result = MagicMock()
        count_result.one.return_value = 2
        campaigns_result = MagicMock()
        campaigns_result.one.return_value = 3
        gm_campaigns_result = MagicMock()
        gm_campaigns_result.one.return_value = 2
        parties_result = MagicMock()
        parties_result.one.return_value = 5

        session = MagicMock()
        session.exec.side_effect = [
            first_result,
            count_result,
            campaigns_result,
            gm_campaigns_result,
            parties_result,
        ]

        result = update_admin_user_service(
            db=session,
            user_id="user-1",
            payload=AdminUserUpdate(role=RoleMode.PLAYER, isSystemAdmin=False),
        )

        self.assertEqual(result.role, RoleMode.PLAYER)
        self.assertFalse(result.isSystemAdmin)
        self.assertEqual(result.displayName, "gm")
        session.commit.assert_called_once()
        session.refresh.assert_called_once_with(user)


class AdminSystemRouteTests(unittest.TestCase):
    def setUp(self):
        self.admin_user = SimpleNamespace(id="user-1", is_system_admin=True)

    @patch("app.api.routes.admin_system.get_admin_overview")
    def test_admin_overview_route_returns_service_payload(self, mock_service):
        mock_service.return_value = AdminOverviewRead(
            usersTotal=10,
            systemAdminsTotal=1,
            campaignsTotal=4,
            partiesTotal=5,
            sessionsTotal=8,
            activeSessionsTotal=2,
            baseItemsActive=100,
            baseItemsInactive=3,
            baseSpellsActive=40,
            baseSpellsInactive=2,
        )

        result = admin_overview(_user=self.admin_user, session=MagicMock())

        self.assertEqual(result.usersTotal, 10)
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.list_admin_users")
    def test_admin_list_users_route_returns_users(self, mock_service):
        mock_service.return_value = [
            AdminUserRead(
                id="user-1",
                username="root",
                displayName="Root",
                role=RoleMode.GM,
                isSystemAdmin=True,
                campaignsCount=2,
                gmCampaignsCount=2,
                partiesCount=1,
                createdAt=datetime.now(timezone.utc),
            )
        ]

        result = admin_list_users(_user=self.admin_user, session=MagicMock())

        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].isSystemAdmin)
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.update_admin_user")
    def test_admin_update_user_route_returns_updated_user(self, mock_service):
        mock_service.return_value = AdminUserRead(
            id="user-2",
            username="player",
            displayName="Player",
            role=RoleMode.PLAYER,
            isSystemAdmin=False,
            campaignsCount=1,
            gmCampaignsCount=0,
            partiesCount=1,
            createdAt=datetime.now(timezone.utc),
        )

        result = admin_update_user(
            "user-2",
            AdminUserUpdate(role=RoleMode.PLAYER),
            _user=self.admin_user,
            session=MagicMock(),
        )

        self.assertEqual(result.username, "player")
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.delete_admin_user")
    def test_admin_delete_user_route_calls_service(self, mock_service):
        response = admin_delete_user("user-2", _user=self.admin_user, session=MagicMock())

        self.assertIsNone(response)
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.list_admin_campaigns")
    def test_admin_list_campaigns_route_returns_campaigns(self, mock_service):
        mock_service.return_value = [
            AdminCampaignRead(
                id="camp-1",
                name="Main Campaign",
                systemType=SystemType.DND5E,
                roleMode=RoleMode.GM,
                gmNames=["Root"],
                membersCount=4,
                partiesCount=1,
                sessionsCount=7,
                activeSessionsCount=1,
                createdAt=datetime.now(timezone.utc),
            )
        ]

        result = admin_list_campaigns(_user=self.admin_user, session=MagicMock())

        self.assertEqual(result[0].name, "Main Campaign")
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.delete_admin_campaign")
    def test_admin_delete_campaign_route_calls_service(self, mock_service):
        response = admin_delete_campaign("camp-1", _user=self.admin_user, session=MagicMock())

        self.assertIsNone(response)
        mock_service.assert_called_once()

    @patch("app.api.routes.admin_system.get_admin_diagnostics")
    def test_admin_diagnostics_route_returns_payload(self, mock_service):
        mock_service.return_value = AdminDiagnosticsRead(
            appEnv="production",
            autoMigrate=False,
            utcNow=datetime.now(timezone.utc),
            databaseOk=True,
            databaseMessage="ok",
            usersTotal=10,
            campaignsTotal=4,
            partiesTotal=5,
            sessionsTotal=8,
            activeSessionsTotal=2,
            activeCombatsTotal=1,
        )

        result = admin_diagnostics(_user=self.admin_user, session=MagicMock())

        self.assertTrue(result.databaseOk)
        mock_service.assert_called_once()


if __name__ == "__main__":
    unittest.main()
