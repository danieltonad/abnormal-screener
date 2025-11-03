import asyncio
from collections import defaultdict
from .socket import CapitalSocket, memory  # Your existing class
from logger import Logger


class CapitalSocketManager:
    MAX_SUBSCRIPTIONS_PER_SOCKET = 40

    def __init__(self):
        self.sockets = []  # List of CapitalSocket instances
        self.subscription_map = defaultdict(list)  # epic -> list of timeframes
        self.socket_assignments = defaultdict(list)  # socket -> list of (epic, timeframe)
        self.lock = asyncio.Lock()

    async def subscribe(self, epic: str, timeframe: str = "MINUTE"):
        if timeframe in self.subscription_map[epic]:
            await Logger.app_log(title="SUBSCRIBE_SKIP", message=f"{epic} {timeframe} already subscribed")
            return

        async with self.lock:
            # critical section: select or create socket safely
            socket = None
            for s in self.sockets:
                if len(self.socket_assignments[s]) < self.MAX_SUBSCRIPTIONS_PER_SOCKET:
                    socket = s
                    break

            if socket is None:
                socket = CapitalSocket()
                self.sockets.append(socket)
                await socket.connect_websocket()

            # update internal maps *before* releasing lock to reserve slot
            self.subscription_map[epic].append(timeframe)
            self.socket_assignments[socket].append((epic, timeframe))

        # now subscribe outside the lock — this part can safely run concurrently
        await socket.subscribe_to_epic(epic, timeframe)

    async def unsubscribe(self, epic: str, timeframe: str = "MINUTE"):
        """Unsubscribe from an epic/timeframe."""
        if timeframe not in self.subscription_map[epic]:
            await Logger.app_log(title="UNSUBSCRIBE_SKIP", message=f"{epic} {timeframe} not subscribed")
            return

        # Find the socket managing this subscription
        socket = None
        for s, subs in self.socket_assignments.items():
            if (epic, timeframe) in subs:
                socket = s
                break

        if socket:
            await socket.unsubscribe_from_epic(epic, timeframe)
            self.socket_assignments[socket].remove((epic, timeframe))
            self.subscription_map[epic].remove(timeframe)

            # Optionally, close socket if it has no subscriptions
            if not self.socket_assignments[socket]:
                await Logger.app_log(title="SOCKET_CLOSE", message="Closing idle socket")
                try:
                    await socket.websocket.close()
                except:
                    pass
                self.sockets.remove(socket)
                del self.socket_assignments[socket]

    async def resubscribe_all(self):
        """Resubscribe all epic/timeframes after reconnects."""
        print("RESUBSCRIBING ALL EPICS")
        temp_map = self.subscription_map.copy()
        self.subscription_map.clear()
        self.socket_assignments.clear()
        self.sockets.clear()

        for epic, timeframes in temp_map.items():
            for tf in timeframes:
                await self.subscribe(epic, tf)

    async def ping_all(self):
        """Ping all sockets to keep connections alive."""
        for socket in self.sockets:
            await socket.ping_socket()


# Example usage
capital_socket = CapitalSocketManager()


