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

    def test_fallback_env_dir_loads_root_env_when_backend_env_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_env_dir = Path(tmp_dir) / "root"
            backend_env_dir = root_env_dir / "apps" / "control-server"
            root_env_dir.mkdir()
            backend_env_dir.mkdir(parents=True)

            (root_env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://root-user:root-pass@db:5432/root\n"
                "JWT_SECRET=root-secret\n"
                "CENTRIFUGO_API_URL=https://root.example.com/api\n"
            )

            environ = {}
            load_env(
                env_dir=backend_env_dir,
                fallback_env_dir=root_env_dir,
                environ=environ,
            )

            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://root-user:root-pass@db:5432/root",
            )
            self.assertEqual(environ["JWT_SECRET"], "root-secret")
            self.assertEqual(environ["CENTRIFUGO_API_URL"], "https://root.example.com/api")

    def test_backend_env_overrides_root_env_when_both_exist(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root_env_dir = Path(tmp_dir) / "root"
            backend_env_dir = root_env_dir / "apps" / "control-server"
            root_env_dir.mkdir()
            backend_env_dir.mkdir(parents=True)

            (root_env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://root-user:root-pass@db:5432/root\n"
                "JWT_SECRET=root-secret\n"
            )
            (backend_env_dir / ".env").write_text(
                "DATABASE_URL=postgresql+psycopg://api-user:api-pass@db:5432/backend\n"
            )

            environ = {}
            load_env(
                env_dir=backend_env_dir,
                fallback_env_dir=root_env_dir,
                environ=environ,
            )

            self.assertEqual(
                environ["DATABASE_URL"],
                "postgresql+psycopg://api-user:api-pass@db:5432/backend",
            )
            self.assertEqual(environ["JWT_SECRET"], "root-secret")

    def test_limiar_map_env_vars_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_dir = Path(tmp_dir)
            (env_dir / ".env").write_text(
                "LIMIAR_MAP_ENABLED=true\n"
                "LIMIAR_MAP_BASE_URL=http://localhost:3000\n"
                "LIMIAR_MAP_TIMEOUT_SECONDS=1.5\n"
            )

            environ = {}
            load_env(env_dir=env_dir, environ=environ)

            self.assertEqual(environ["LIMIAR_MAP_ENABLED"], "true")
            self.assertEqual(environ["LIMIAR_MAP_BASE_URL"], "http://localhost:3000")
            self.assertEqual(environ["LIMIAR_MAP_TIMEOUT_SECONDS"], "1.5")

    def test_default_backend_layout_discovers_monorepo_root_env(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            monorepo_root = Path(tmp_dir) / "repo"
            backend_env_dir = monorepo_root / "apps" / "control-server"
            monorepo_root.mkdir()
            backend_env_dir.mkdir(parents=True)

            (monorepo_root / ".env").write_text(
                "CENTRIFUGO_API_KEY=root-api-key\n"
                "CENTRIFUGO_TOKEN_SECRET=root-token-secret\n"
            )

            environ = {}
            load_env(env_dir=backend_env_dir, fallback_env_dir=None, environ=environ)

            self.assertEqual(environ["CENTRIFUGO_API_KEY"], "root-api-key")
            self.assertEqual(environ["CENTRIFUGO_TOKEN_SECRET"], "root-token-secret")


if __name__ == "__main__":
    unittest.main()
