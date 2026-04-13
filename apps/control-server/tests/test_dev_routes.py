import unittest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes import dev
from app.core.config import settings


class DevRoutesTests(unittest.TestCase):
    def test_reset_database_requires_development_mode(self):
        previous_env = settings.app_env
        settings.app_env = "production"
        try:
            with self.assertRaises(HTTPException) as ctx:
                dev.reset_database(session=MagicMock())
        finally:
            settings.app_env = previous_env

        self.assertEqual(ctx.exception.status_code, 403)

    def test_reset_database_truncates_tables(self):
        previous_env = settings.app_env
        settings.app_env = "development"
        try:
            session = MagicMock()
            with patch(
                "app.api.routes.dev.truncate_all_application_tables",
                return_value=["app_user", "campaign"],
            ) as truncate_tables:
                result = dev.reset_database(session=session)
        finally:
            settings.app_env = previous_env

        self.assertTrue(result["ok"])
        self.assertEqual(result["tables"], ["app_user", "campaign"])
        truncate_tables.assert_called_once_with(session)
        session.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
