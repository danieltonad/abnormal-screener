import asyncio
import json
import websockets
from uuid import uuid4
from logger import Logger
from .memory import memory


class CapitalSocket:
    URI = "wss://api-streaming-capital.backend-capital.com/connect"

    def __init__(self):
        self.websocket = None
        self.listener_task = None
        self.on_close = None

        self.running = False
        self.connected = False

        self.subscribed_epics = set()
        self.correlation_id = str(uuid4())

        self._connect_lock = asyncio.Lock()

    # ───────────────────────────────
    # Connection
    # ───────────────────────────────

    async def connect_websocket(self):
        async with self._connect_lock:
            if self.connected:
                return

            try:
                self.websocket = await websockets.connect(
                    self.URI,
                    ping_interval=None,   # Capital prefers app-level ping
                    ping_timeout=None,
                )

                self.connected = True
                self.running = True

                await Logger.app_log(
                    title="WS_CONNECT",
                    message="WebSocket transport connected"
                )

                self.listener_task = asyncio.create_task(self._listen())

                # remove later
                # await self.subscribe_to_epic("BTCUSD", timeframe="MKT_DATA", ohlc=False)
                # await self.subscribe_to_epic("GOLD", timeframe="MKT_DATA_GOLD", ohlc=False)
                # await self.subscribe_to_epic("NFLX", timeframe="MKT_DATA_GOLD", ohlc=False)

            except Exception as e:
                await Logger.app_log(
                    title="WS_CONNECT_ERR",
                    message=str(e)
                )
                await self.close()
                raise

    # ───────────────────────────────
    # Subscriptions
    # ───────────────────────────────

    async def subscribe_to_epic(
        self,
        epic: str,
        timeframe: str = "MINUTE",
        ohlc: bool = True
    ):
        if not self.connected:
            raise RuntimeError("WebSocket not connected")

        key = f"{epic}<=>{timeframe}"
        if key in self.subscribed_epics:
            return

        if ohlc:
            msg = {
                "destination": "OHLCMarketData.subscribe",
                "correlationId": f"SUB_{epic}_{timeframe}_{uuid4()}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                "payload": {
                    "epics": [epic],
                    "resolutions": [timeframe],
                    "type": "classic"
                }
            }
        else:
            msg = {
                "destination": "marketData.subscribe",
                "correlationId": f"SUB_{epic}_{uuid4()}",
                "cst": memory.capital_auth_header["CST"],
                "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
                "payload": {
                    "epics": [epic]
                }
            }

        await self.websocket.send(json.dumps(msg))
        if ohlc:
            self.subscribed_epics.add(key)

        await Logger.app_log(
            title="SUBSCRIBE_SENT",
            message=f"{epic} [{timeframe}]"
        )

    async def unsubscribe_from_epic(self, epic: str, timeframe: str = "MINUTE"):
        if not self.connected:
            return

        key = f"{epic}<=>{timeframe}"
        if key not in self.subscribed_epics:
            return

        msg = {
            "destination": "OHLCMarketData.unsubscribe",
            "correlationId": f"UNSUB_{epic}_{timeframe}_{uuid4()}",
            "cst": memory.capital_auth_header["CST"],
            "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
            "payload": {
                "epics": [epic],
                "resolutions": [timeframe],
                "type": "classic"
            }
        }

        await self.websocket.send(json.dumps(msg))
        self.subscribed_epics.remove(key)

        await Logger.app_log(
            title="UNSUBSCRIBE_SENT",
            message=f"{epic} [{timeframe}]"
        )

    # ───────────────────────────────
    # Listener
    # ───────────────────────────────

    async def _listen(self):
        from .event import faster_event_signal, gold_signal

        try:
            while self.running:
                raw = await self.websocket.recv()

                # log raw payloads when debugging weirdness
                data = json.loads(raw)
                destination = data.get("destination")

                if data.get("status") == "ERROR":
                    await Logger.app_log(
                        title="WS_ERROR",
                        message=json.dumps(data)
                    )
                    continue

                if destination == "ohlc.event":
                    p = data["payload"]


                    memory.update_ohlc_data(
                        epic=p["epic"],
                        resolution=p["resolution"],
                        timestamp=p["t"],
                        open=p["o"],
                        high=p["h"],
                        low=p["l"],
                        close=p["c"],
                        price_type=p["priceType"],
                    )
                    
                    await faster_event_signal(
                        p["epic"],
                        p["resolution"],
                        p["priceType"]
                    )
                    
                    await gold_signal(
                        p["epic"],
                        p["resolution"],
                        p["priceType"]
                    )

                # else:
                #     await Logger.app_log(
                #         title="WS_EVENT",
                #         message=json.dumps(data)
                #     )
        
        except asyncio.CancelledError:
            pass

        except websockets.exceptions.ConnectionClosed:
            await Logger.app_log(
                title="WS_CLOSED",
                message="WebSocket closed by server"
            )

        except Exception as e:
            await Logger.app_log(
                title="WS_LISTEN_ERR",
                message=str(e)
            )

        finally:
            self.running = False
            self.connected = False

            if self.on_close:
                await self.on_close(self)
            
            await self.reconnect()

    # ───────────────────────────────
    # Ping & close
    # ───────────────────────────────

    async def ping_socket(self):
        if not self.connected:
            return

        msg = {
            "destination": "ping",
            "correlationId": f"PING_{self.correlation_id}",
            "cst": memory.capital_auth_header["CST"],
            "securityToken": memory.capital_auth_header["X-SECURITY-TOKEN"],
        }

        await self.websocket.send(json.dumps(msg))

    async def close(self):
        self.running = False

        if self.listener_task:
            self.listener_task.cancel()

        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass

        self.websocket = None
        self.connected = False


    async def reconnect(self):
        await self.close()
        epics = list(self.subscribed_epics)
        self.subscribed_epics.clear()
        for conn in epics:
            epic, timeframe = conn.split("<=>")
            await self.subscribe_to_epic(epic, timeframe)
