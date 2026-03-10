import os
from pathlib import Path


def parse_cors_origins(raw: str) -> list[str]:
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def load_env() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/limiarcontrol",
    )
    port: int = int(os.getenv("PORT", "3000"))
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:5173")
    cors_origins: list[str] = parse_cors_origins(cors_origin)
    app_env: str = os.getenv("APP_ENV", "development")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    centrifugo_api_url: str = os.getenv(
        "CENTRIFUGO_API_URL",
        "http://centrifugo:8000/api",
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


settings = Settings()
