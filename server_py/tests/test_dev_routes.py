import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routes import dev
from app.core.config import settings


class DevRoutesTests(unittest.TestCase):
    def test_sync_base_csvs_requires_development_mode(self):
        previous_env = settings.app_env
        settings.app_env = "production"
        try:
            with self.assertRaises(HTTPException) as ctx:
                dev.sync_base_csvs(_user=SimpleNamespace())
        finally:
            settings.app_env = previous_env

        self.assertEqual(ctx.exception.status_code, 403)

    def test_sync_base_csvs_runs_both_importers(self):
        previous_env = settings.app_env
        settings.app_env = "development"
        try:
            with patch(
                "app.api.routes.dev._run_python_script",
                side_effect=[
                    {
                        "script": "import_dnd_base_items.py",
                        "ok": True,
                        "exitCode": 0,
                        "stdoutTail": "items ok",
                        "stderrTail": None,
                    },
                    {
                        "script": "import_dnd_base_spells.py",
                        "ok": True,
                        "exitCode": 0,
                        "stdoutTail": "spells ok",
                        "stderrTail": None,
                    },
                ],
            ) as run_script:
                result = dev.sync_base_csvs(_user=SimpleNamespace())
        finally:
            settings.app_env = previous_env

        self.assertTrue(result["ok"])
        self.assertEqual(len(result["scripts"]), 2)
        self.assertEqual(
            [call.args[0] for call in run_script.call_args_list],
            list(dev.SYNC_SCRIPTS),
        )

    def test_sync_base_csvs_returns_http_500_when_a_script_fails(self):
        previous_env = settings.app_env
        settings.app_env = "development"
        try:
            with patch(
                "app.api.routes.dev._run_python_script",
                side_effect=[
                    {
                        "script": "import_dnd_base_items.py",
                        "ok": True,
                        "exitCode": 0,
                        "stdoutTail": "items ok",
                        "stderrTail": None,
                    },
                    {
                        "script": "import_dnd_base_spells.py",
                        "ok": False,
                        "exitCode": 1,
                        "stdoutTail": None,
                        "stderrTail": "boom",
                    },
                ],
            ):
                with self.assertRaises(HTTPException) as ctx:
                    dev.sync_base_csvs(_user=SimpleNamespace())
        finally:
            settings.app_env = previous_env

        self.assertEqual(ctx.exception.status_code, 500)
        detail = ctx.exception.detail
        self.assertIn("import_dnd_base_spells.py", detail["message"])
        self.assertEqual(len(detail["scripts"]), 2)


if __name__ == "__main__":
    unittest.main()
