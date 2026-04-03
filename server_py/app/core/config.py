import os
from collections.abc import MutableMapping
from pathlib import Path


def parse_cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(
    env_path: Path,
    locked_keys: set[str],
    environ: MutableMapping[str, str] | None = None,
) -> None:
    environ = environ if environ is not None else os.environ
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in locked_keys:
            continue
        environ[key] = value.strip()


def resolve_env_path(env_dir: Path, raw_path: str) -> Path:
    env_path = Path(raw_path)
    if env_path.is_absolute():
        return env_path
    return env_dir / env_path


def iter_env_dirs(env_dir: Path, fallback_env_dir: Path | None = None) -> list[Path]:
    env_dirs: list[Path] = []
    if fallback_env_dir and fallback_env_dir != env_dir:
        env_dirs.append(fallback_env_dir)
    env_dirs.append(env_dir)
    return env_dirs


def load_env(
    env_dir: Path | None = None,
    fallback_env_dir: Path | None = None,
    environ: MutableMapping[str, str] | None = None,
) -> None:
    environ = environ if environ is not None else os.environ
    default_env_dir = Path(__file__).resolve().parents[2]
    env_dir = env_dir if env_dir is not None else default_env_dir
    if fallback_env_dir is None and env_dir == default_env_dir:
        fallback_env_dir = default_env_dir.parent
    locked_keys = set(environ.keys())

    explicit_env_file = environ.get("APP_ENV_FILE")
    if explicit_env_file:
        explicit_candidates = [
            resolve_env_path(candidate_env_dir, explicit_env_file)
            for candidate_env_dir in iter_env_dirs(env_dir, fallback_env_dir)
        ]
        explicit_path = next(
            (candidate for candidate in explicit_candidates if candidate.exists()),
            explicit_candidates[-1],
        )
        load_env_file(explicit_path, locked_keys=locked_keys, environ=environ)
        return

    app_env = environ.get("APP_ENV", "development")
    for candidate_env_dir in iter_env_dirs(env_dir, fallback_env_dir):
        load_env_file(candidate_env_dir / ".env", locked_keys=locked_keys, environ=environ)
    for candidate_env_dir in iter_env_dirs(env_dir, fallback_env_dir):
        load_env_file(
            candidate_env_dir / ".env.local",
            locked_keys=locked_keys,
            environ=environ,
        )

    for candidate_env_dir in iter_env_dirs(env_dir, fallback_env_dir):
        load_env_file(
            candidate_env_dir / f".env.{app_env}",
            locked_keys=locked_keys,
            environ=environ,
        )
    for candidate_env_dir in iter_env_dirs(env_dir, fallback_env_dir):
        load_env_file(
            candidate_env_dir / f".env.{app_env}.local",
            locked_keys=locked_keys,
            environ=environ,
        )


load_env()
DEFAULT_APP_ENV = os.getenv("APP_ENV", "development")
DEFAULT_AUTO_MIGRATE = DEFAULT_APP_ENV == "development"


_INSECURE_DEFAULTS = frozenset({"dev-secret-change-me", "dev-api-key", ""})


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol",
    )
    port: int = int(os.getenv("PORT", "3000"))
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    cors_origins: list[str] = parse_cors_origins(cors_origin)
    app_env: str = DEFAULT_APP_ENV
    auto_migrate: bool = parse_bool(
        os.getenv("AUTO_MIGRATE"), default=DEFAULT_AUTO_MIGRATE
    )
    db_startup_retries: int = int(os.getenv("DB_STARTUP_RETRIES", "5"))
    db_startup_retry_delay_seconds: float = float(
        os.getenv("DB_STARTUP_RETRY_DELAY_SECONDS", "1.5")
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    centrifugo_api_url: str = os.getenv(
        "CENTRIFUGO_API_URL",
        "http://localhost:8001/api",
    )
    centrifugo_api_key: str = os.getenv("CENTRIFUGO_API_KEY", "dev-api-key")
    centrifugo_public_url: str = os.getenv(
        "CENTRIFUGO_PUBLIC_URL",
        "ws://localhost:8001/connection/websocket",
    )
    centrifugo_token_secret: str = os.getenv(
        "CENTRIFUGO_TOKEN_SECRET",
        jwt_secret,
    )
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")

    def validate_production_secrets(self) -> None:
        if self.app_env == "development":
            return
        errors: list[str] = []
        if self.jwt_secret in _INSECURE_DEFAULTS:
            errors.append("JWT_SECRET must be set to a strong value in production")
        if self.centrifugo_api_key in _INSECURE_DEFAULTS:
            errors.append("CENTRIFUGO_API_KEY must be set to a strong value in production")
        if self.centrifugo_token_secret in _INSECURE_DEFAULTS:
            errors.append("CENTRIFUGO_TOKEN_SECRET must be set to a strong value in production")
        if "postgres:postgres@" in self.database_url:
            errors.append("DATABASE_URL must use strong credentials in production")
        if errors:
            raise RuntimeError(
                "Insecure configuration detected:\n  - " + "\n  - ".join(errors)
            )


settings = Settings()
settings.validate_production_secrets()
