import websockets
import asyncio
import json
from .memory import memory
from logger import Logger
from settings import settings


class CapitalSocket:
    def __init__(self):
        self.websocket = None
        self.running = False
        self.subscribed_epics = set()
        self._listen_task = None
        self._reconnect_lock = asyncio.Lock()
        self._ping_interval = 30  # seconds

    async def connect_websocket(self):
        """Connect to Capital.com WebSocket if not already connected."""
        if self.websocket and self.running:
            return

        try:
            uri = "wss://api-streaming-capital.backend-capital.com/connect"
            self.websocket = await websockets.connect(
                uri, ping_interval=60, ping_timeout=30
            )
            self.running = True
            await Logger.app_log(title="WS_CONNECT", message="WebSocket connected")

            if not self._listen_task or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen())
            asyncio.create_task(self._ping_loop())

        except Exception as e:
            await Logger.app_log(title="WS_CONNECT_ERR", message=str(e))
            await self._schedule_reconnect()

    async def _ping_loop(self):
        """Periodically ping the WebSocket to keep connection alive."""
        while self.running and self.websocket:
            await asyncio.sleep(self._ping_interval)
            await self.ping_socket()

    async def ping_socket(self):
        """Send ping message to WebSocket."""
        try:
            if not self.running or not self.websocket:
                return

            ping_msg = {
                "destination": "ping",
                "correlationId": "ping_XGXXXTX",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"]
            }
            await self.websocket.send(json.dumps(ping_msg))

        except Exception as e:
            await Logger.app_log(title="PING_ERR", message=f"Ping failed: {str(e)}")
            await self._schedule_reconnect()

    async def subscribe_to_epic(self, epic: str, timeframe: str = "MINUTE"):
        """Subscribe to real-time data for a given epic."""
        try:
            await self.connect_websocket()

            key = f"{epic}_{timeframe}"
            if key in self.subscribed_epics:
                await Logger.app_log(title="SUBSCRIBE_SKIP", message=f"{epic} [{timeframe}] already subscribed")
                return

            subscribe_msg = {
                "destination": "OHLCMarketData.subscribe",
                "correlationId": f"epic_sub_{epic}_{timeframe}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                "payload": {
                    "epics": [epic],
                    "resolutions": [timeframe],
                    "type": "classic"
                }
            }
            await self.websocket.send(json.dumps(subscribe_msg))
            self.subscribed_epics.add(key)
            await Logger.app_log(title="SUBSCRIBE_SENT", message=f"Subscribed to {epic} [{timeframe}]")

        except Exception as e:
            await Logger.app_log(title="SUBSCRIBE_ERR", message=f"{epic} [{timeframe}]: {str(e)}")
            await asyncio.sleep(5)
            # Retry once
            if self.running:
                await self.subscribe_to_epic(epic, timeframe)

    async def unsubscribe_from_epic(self, epic: str, timeframe: str = "MINUTE"):
        """Unsubscribe from real-time data for a given epic."""
        key = f"{epic}_{timeframe}"
        # if key not in self.subscribed_epics:
        #     await Logger.app_log(title="UNSUBSCRIBE_SKIP", message=f"{epic} [{timeframe}] not subscribed")
        #     return

        try:
            unsubscribe_msg = {
                "destination": "OHLCMarketData.unsubscribe",
                "correlationId": f"epic_sub_{epic}_{timeframe}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                "payload": {
                    "epics": [epic],
                    "resolutions": [timeframe],
                    "type": "classic"
                }
            }
            await self.websocket.send(json.dumps(unsubscribe_msg))
            self.subscribed_epics.remove(key)
            await Logger.app_log(title="UNSUBSCRIBE_SENT", message=f"Unsubscribed from {epic} [{timeframe}]")

        except Exception as e:
            await Logger.app_log(title="UNSUBSCRIBE_ERR", message=f"{epic} [{timeframe}]: {str(e)}")

    async def _listen(self):
        """Listen for incoming WebSocket messages and handle reconnections."""
        from .event import event_signal  # Avoid circular import
        try:
            while self.running and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=300)
                    data = json.loads(message)

                    destination = data.get("destination")
                    if destination == "OHLCMarketData.subscribe":
                        await Logger.app_log(
                            title="SUBSCRIBE_CONFIRM",
                            message=f"Subscription confirmed: {data['payload']['subscriptions']}"
                        )
                    elif destination == "OHLCMarketData.unsubscribe":
                        await Logger.app_log(
                            title="UNSUBSCRIBE_CONFIRM",
                            message=f"Unsubscription confirmed: {data['payload']['subscriptions']}"
                        )
                    elif destination == "ohlc.event":
                        payload = data["payload"]
                        memory.update_ohlc_data(
                            epic=payload["epic"],
                            resolution=payload["resolution"],
                            timestamp=payload["t"],
                            open=payload["o"],
                            high=payload["h"],
                            low=payload["l"],
                            close=payload["c"],
                            price_type=payload["priceType"]
                        )
                        # Trigger event signal processing
                        await event_signal(payload["epic"], payload["resolution"])


                except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
                    await Logger.app_log(title="WS_LISTEN_ERR", message=str(e))
                    break

        except Exception as e:
            await Logger.app_log(title="WS_LISTEN_ERR", message=f"Unhandled: {str(e)}")

        finally:
            await self._schedule_reconnect()

    async def _schedule_reconnect(self):
        """Ensure only one reconnect happens at a time."""
        async with self._reconnect_lock:
            if not self.running:
                return

            await Logger.app_log(title="WS_RECONNECT", message="Reconnecting WebSocket...")
            self.running = False

            if self.websocket:
                try:
                    await self.websocket.close()
                except Exception as e:
                    await Logger.app_log(title="WS_CLOSE_ERR", message=str(e))
                self.websocket = None

            # Exponential backoff
            delay = 1
            for attempt in range(5):
                try:
                    await asyncio.sleep(delay)
                    await self.connect_websocket()
                    
                    # Resubscribe to all previous epics
                    for key in list(self.subscribed_epics):
                        epic, timeframe = key.rsplit("_", 1)
                        await self.subscribe_to_epic(epic, timeframe)
                        await asyncio.sleep(0.2)
                    return
                except Exception as e:
                    await Logger.app_log(title="WS_RECONNECT_ERR", message=str(e))
                    delay *= 2

            await Logger.app_log(title="WS_RECONNECT_FAIL", message="Failed to reconnect after multiple attempts.")
