import httpx

from app.core.config import settings


class CentrifugoClient:
    def __init__(self) -> None:
        self._api_url = settings.centrifugo_api_url
        self._headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.centrifugo_api_key,
        }
        self._http: httpx.AsyncClient | None = None

    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=5.0)
        return self._http

    async def publish(self, channel: str, data: dict) -> None:
        resp = await self._client().post(
            f"{self._api_url}/publish",
            json={"channel": channel, "data": data},
            headers=self._headers,
        )
        resp.raise_for_status()

    async def presence(self, channel: str) -> dict:
        resp = await self._client().post(
            f"{self._api_url}/presence",
            json={"channel": channel},
            headers=self._headers,
        )
        resp.raise_for_status()
        return resp.json().get("result", {})

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()


centrifugo = CentrifugoClient()
