import tempfile
import unittest
from pathlib import Path

from app.core.config import load_env


class TestConfigEnvLoading(unittest.TestCase):
    def test_defaults_to_development_local_when_shell_app_env_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_dir = Path(tmp_dir)
            (env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://prod-user:prod-pass@db:5432/prod\n"
                "APP_ENV=production\n"
                "CENTRIFUGO_API_URL=https://rt.example.com/api\n"
            )
            (env_dir / ".env.development.local").write_text(
                "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dev\n"
                "APP_ENV=development\n"
                "CENTRIFUGO_API_URL=http://localhost:8001/api\n"
            )

            environ = {}
            load_env(env_dir=env_dir, environ=environ)

            self.assertEqual(environ["APP_ENV"], "development")
            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://postgres:postgres@localhost:5432/dev",
            )
            self.assertEqual(environ["CENTRIFUGO_API_URL"], "http://localhost:8001/api")

    def test_app_env_file_loads_only_explicit_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_dir = Path(tmp_dir)
            (env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://prod-user:prod-pass@db:5432/prod\n"
                "JWT_SECRET=prod-secret\n"
            )
            (env_dir / ".env.development.local").write_text(
                "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dev\n"
                "APP_ENV=development\n"
            )

            environ = {"APP_ENV_FILE": ".env.development.local"}
            load_env(env_dir=env_dir, environ=environ)

            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://postgres:postgres@localhost:5432/dev",
            )
            self.assertEqual(environ["APP_ENV"], "development")
            self.assertNotIn("JWT_SECRET", environ)

    def test_existing_environment_variables_win_over_env_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_dir = Path(tmp_dir)
            (env_dir / ".env.development.local").write_text(
                "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dev\n"
            )

            environ = {
                "APP_ENV_FILE": ".env.development.local",
                "DATABASE_URL": "postgresql+psycopg://shell-user:shell-pass@db:5432/shell",
            }
            load_env(env_dir=env_dir, environ=environ)

            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://shell-user:shell-pass@db:5432/shell",
            )

    def test_app_env_loads_mode_specific_local_override(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_dir = Path(tmp_dir)
            (env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://prod-user:prod-pass@db:5432/prod\n"
                "JWT_SECRET=shared-secret\n"
            )
            (env_dir / ".env.development.local").write_text(
                "DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/dev\n"
                "CENTRIFUGO_API_URL=http://localhost:8001/api\n"
            )

            environ = {"APP_ENV": "development"}
            load_env(env_dir=env_dir, environ=environ)

            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://postgres:postgres@localhost:5432/dev",
            )
            self.assertEqual(environ["JWT_SECRET"], "shared-secret")
            self.assertEqual(environ["CENTRIFUGO_API_URL"], "http://localhost:8001/api")


if __name__ == "__main__":
    unittest.main()
