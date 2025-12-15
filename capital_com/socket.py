import websockets
import asyncio
import json
from .memory import memory
from logger import Logger
from uuid import uuid4


class CapitalSocket:
    def __init__(self):
        self.websocket = None
        self.running = False
        self.subscribed_epics = set()
        self._listen_task = None
        self._reconnect_lock = asyncio.Lock()
        self.correlation_id = str(uuid4())

    async def connect_websocket(self):
        """Connect to Capital.com WebSocket if not already connected."""
        # if self.websocket and self.running:
        #     print("WebSocket already connected.")
        #     return

        try:
            uri = "wss://api-streaming-capital.backend-capital.com/connect"

            # IMPORTANT:
            # No ping_interval, no ping_timeout → avoid transport ping failures.
            self.websocket = await websockets.connect(uri)

            self.running = True
            await Logger.app_log(title="WS_CONNECT", message="WebSocket connected")

            if not self._listen_task or self._listen_task.done():
                self._listen_task = asyncio.create_task(self._listen())

        except Exception as e:
            await Logger.app_log(title="WS_CONNECT_ERR", message=str(e))
            await self._schedule_reconnect()

    def _is_socket_closed(self):
        ws = self.websocket
        if ws is None:
            return True

        if hasattr(ws, "closed"):
            return ws.closed

        if hasattr(ws, "closed_connection"):
            return ws.closed_connection

        return True

    async def ping_socket(self):
        """
        Send JSON ping to Capital.com.
        This is manually called (cron), not looped.
        """
        try:
            if not self.websocket:
                print("WebSocket not connected, cannot ping.")
                return

            ping_msg = {
                "destination": "ping",
                "correlationId": f"SOCKET_{self.correlation_id}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"]
            }

            await self.websocket.send(json.dumps(ping_msg))

            print("WS_PING_SENT")

        except Exception as e:
            await Logger.app_log(title="PING_ERR", message=f"Ping failed: {str(e)}")

    async def subscribe_to_epic(self, epic: str, timeframe: str = "MINUTE", ohlc: bool = True):
        """Subscribe to real-time data for a given epic."""
        try:
            await self.connect_websocket()
            key = f"{epic}<=>{timeframe}"

            if ohlc:
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
            else:
                subscribe_msg = {
                    "destination": "marketData.subscribe",
                    "correlationId": f"epic_sub_{epic}",
                    "cst": memory.capital_auth_header["CST"],
                    "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                    "payload": {"epics": [epic]}
                }

            await self.websocket.send(json.dumps(subscribe_msg))
            self.subscribed_epics.add(key)

        except Exception as e:
            await Logger.app_log(title="SUBSCRIBE_ERR", message=f"{epic} [{timeframe}]: {str(e)}")
            await asyncio.sleep(5)
            if self.running:
                await self.subscribe_to_epic(epic, timeframe)

    async def unsubscribe_from_epic(self, epic: str, timeframe: str = "MINUTE"):
        """Unsubscribe from real-time data for a given epic."""
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
            await Logger.app_log(title="UNSUBSCRIBE_SENT", message=f"Unsubscribed from {epic} [{timeframe}]")

        except Exception as e:
            await Logger.app_log(title="UNSUBSCRIBE_ERR", message=f"{epic} [{timeframe}]: {str(e)}")

    async def _listen(self):
        from .event import faster_event_signal, stocks_event_signal
        try:
            while self.running and self.websocket:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(),timeout=5000)
                    data = json.loads(message)
                    print(data)

                    destination = data.get("destination")

                    if destination == "OHLCMarketData.unsubscribe":
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

                        # await stocks_event_signal(payload["epic"], payload["resolution"])
                        await faster_event_signal(payload["epic"], payload["resolution"])

                except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosedError) as e:
                    await Logger.app_log(title="WS_LISTEN_ERR", message=str(e))
                    break

        except Exception as e:
            await Logger.app_log(title="WS_LISTEN_ERR", message=f"Unhandled: {str(e)}")

        finally:
            await self._schedule_reconnect()

    
    
    async def _schedule_reconnect(self):
        """Reconnect safely."""
        async with self._reconnect_lock:
            if not self.running:
                print("WebSocket not running, no reconnect needed.")
                return

            await Logger.app_log(title="WS_RECONNECT", message="Reconnecting WebSocket...")

            if self.websocket:
                try:
                    await self.websocket.close()
                except Exception as e:
                    await Logger.app_log(title="WS_CLOSE_ERR", message=str(e))
                self.websocket = None

            delay = 1
            for attempt in range(5):
                try:
                    await asyncio.sleep(delay)
                    await self.connect_websocket()

                    # Re-subscribe
                    for key in list(self.subscribed_epics):
                        epic, timeframe = key.split("<=>")
                        await self.subscribe_to_epic(epic, timeframe)
                        await asyncio.sleep(0.2)

                    return
                except Exception as e:
                    await Logger.app_log(title="WS_RECONNECT_ERR", message=str(e))
                    delay *= 2

            await Logger.app_log(title="WS_RECONNECT_FAIL",
                                 message="Failed to reconnect after multiple attempts.")
