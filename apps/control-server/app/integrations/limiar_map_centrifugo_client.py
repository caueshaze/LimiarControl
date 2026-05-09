from __future__ import annotations

import asyncio
import logging
from threading import Event, RLock, Thread
from typing import Any, Callable
import time

from centrifuge import Client
from centrifuge.handlers import ClientEventHandler, SubscriptionEventHandler
from app.core.config import settings
from app.core.auth import encode_jwt

logger = logging.getLogger(__name__)

RealtimeEventHandler = Callable[[str, dict[str, Any]], None]
MAP_SYSTEM_EVENTS_CHANNEL = "system:map_events"


class _LimiarMapClientEvents(ClientEventHandler):
    def __init__(self, channels: tuple[str, ...]) -> None:
        self._channels = channels

    async def on_connected(self, ctx: Any) -> None:
        logger.info(
            "LimiarMap centrifugo connected channels=%s ctx=%s",
            self._channels,
            ctx,
        )

    async def on_disconnected(self, ctx: Any) -> None:
        logger.warning(
            "LimiarMap centrifugo disconnected channels=%s ctx=%s",
            self._channels,
            ctx,
        )

    async def on_error(self, ctx: Any) -> None:
        logger.error("LimiarMap centrifugo error ctx=%s", ctx)


class _LimiarMapSubscriptionEvents(SubscriptionEventHandler):
    def __init__(
        self,
        *,
        channel: str,
        event_handler: RealtimeEventHandler,
    ) -> None:
        self._channel = channel
        self._event_handler = event_handler

    async def on_publication(self, ctx: Any) -> None:
        payload = ctx.pub.data
        if not isinstance(payload, dict):
            logger.warning(
                "LimiarMap centrifugo ignored non-dict payload channel=%s payload_type=%s",
                self._channel,
                type(payload).__name__,
            )
            return
        event_type = payload.get("eventType")
        if not isinstance(event_type, str):
            logger.warning(
                "LimiarMap centrifugo ignored payload without eventType channel=%s",
                self._channel,
            )
            return
        try:
            self._event_handler(event_type, payload)
        except Exception:
            logger.exception(
                "LimiarMap centrifugo handler crashed channel=%s event=%s",
                self._channel,
                event_type,
            )

    async def on_subscribed(self, ctx: Any) -> None:
        logger.info(
            "LimiarMap centrifugo subscribed channel=%s ctx=%s",
            self._channel,
            ctx,
        )

    async def on_unsubscribed(self, ctx: Any) -> None:
        logger.warning(
            "LimiarMap centrifugo unsubscribed channel=%s ctx=%s",
            self._channel,
            ctx,
        )

    async def on_error(self, ctx: Any) -> None:
        logger.error(
            "LimiarMap centrifugo subscription error channel=%s ctx=%s",
            self._channel,
            ctx,
        )


class LimiarMapCentrifugoClient:
    def __init__(
        self,
        *,
        ws_url: str,
        event_handler: RealtimeEventHandler,
        channels: tuple[str, ...] = (MAP_SYSTEM_EVENTS_CHANNEL,),
    ) -> None:
        self._ws_url = ws_url
        self._event_handler = event_handler
        self._channels = tuple(dict.fromkeys(channels)) or (MAP_SYSTEM_EVENTS_CHANNEL,)
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._lock = RLock()
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run_forever,
                name="limiar-map-centrifugo-client",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._stop_event.set()
            loop = self._loop
            thread = self._thread

        if loop is not None and loop.is_running():
            loop.call_soon_threadsafe(self._stop_loop)

        if thread is not None:
            thread.join(timeout=3.0)

        with self._lock:
            self._thread = None
            self._loop = None

    def _stop_loop(self) -> None:
        if self._loop is None:
            return
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    def _run_forever(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop

        try:
            loop.run_until_complete(self._async_run_forever())
        except asyncio.CancelledError:
            pass
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def _generate_connection_token(self) -> str:
        payload = {
            "sub": "limiarControl",
            "exp": int(time.time()) + 60 * 60 * 24 * 7,
            "info": {
                "displayName": "LimiarControl System",
            },
        }
        return encode_jwt(payload, settings.centrifugo_token_secret)

    def _generate_subscription_token(self, channel: str) -> str:
        payload = {
            "sub": "limiarControl",
            "channel": channel,
            "exp": int(time.time()) + 60 * 60 * 24 * 7,
        }
        return encode_jwt(payload, settings.centrifugo_token_secret)

    async def _async_run_forever(self) -> None:
        while not self._stop_event.is_set():
            logger.info(
                "LimiarMap centrifugo starting connection cycle ws_url=%s channels=%s",
                self._ws_url,
                self._channels,
            )
            client = Client(
                self._ws_url,
                events=_LimiarMapClientEvents(self._channels),
                token=self._generate_connection_token(),
            )

            subscriptions = []
            for channel in self._channels:
                sub = client.new_subscription(
                    channel,
                    events=_LimiarMapSubscriptionEvents(
                        channel=channel,
                        event_handler=self._event_handler,
                    ),
                    token=self._generate_subscription_token(channel)
                )
                subscriptions.append(sub)

            try:
                await client.connect()
                for sub in subscriptions:
                    await sub.subscribe()

                while not self._stop_event.is_set():
                    await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(
                    "LimiarMap centrifugo connection cycle error exc=%s", exc
                )
                if not self._stop_event.is_set():
                    await asyncio.sleep(2.0)
            finally:
                if client.state.name != "disconnected":
                    try:
                        await client.disconnect()
                    except Exception:
                        logger.debug(
                            "LimiarMap centrifugo disconnect raised unexpectedly",
                            exc_info=True,
                        )
