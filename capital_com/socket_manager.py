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

    async def subscribe(self, epic: str, timeframe: str = "MINUTE"):
        """Subscribe to an epic/timeframe, managing socket limits."""
        # Check if already subscribed
        if timeframe in self.subscription_map[epic]:
            await Logger.app_log(title="SUBSCRIBE_SKIP", message=f"{epic} {timeframe} already subscribed")
            return

        # Find a socket with available slots
        socket = None
        for s in self.sockets:
            if len(self.socket_assignments[s]) < self.MAX_SUBSCRIPTIONS_PER_SOCKET:
                socket = s
                break

        # If no socket available, create a new one
        if socket is None:
            socket = CapitalSocket()
            self.sockets.append(socket)
            await socket.connect_websocket()

        # Subscribe on the selected socket
        await socket.subscribe_to_epic(epic, timeframe)

        # Update internal mappings
        self.subscription_map[epic].append(timeframe)
        self.socket_assignments[socket].append((epic, timeframe))

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


