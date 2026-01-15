import asyncio
from collections import defaultdict
from logger import Logger
from .socket import CapitalSocket, memory


class CapitalSocketManager:
    MAX_SUBSCRIPTIONS_PER_SOCKET = 40

    def __init__(self):
        self.sockets = []
        self.subscription_map = defaultdict(set)     # epic -> {timeframes}
        self.socket_assignments = defaultdict(set)   # socket -> {(epic, timeframe)}
        self.lock = asyncio.Lock()

    # ───────────────────────────────
    # Public API
    # ───────────────────────────────

    async def subscribe(self, epic: str, timeframe: str = "MINUTE"):
        async with self.lock:
            if timeframe in self.subscription_map[epic]:
                await Logger.app_log(
                    title="SUBSCRIBE_SKIP",
                    message=f"{epic} {timeframe} already subscribed"
                )
                return

            socket = await self._get_or_create_socket()

            self.subscription_map[epic].add(timeframe)
            self.socket_assignments[socket].add((epic, timeframe))

        # I/O outside lock
        await socket.subscribe_to_epic(epic, timeframe)

    async def unsubscribe(self, epic: str, timeframe: str = "MINUTE"):
        async with self.lock:
            if timeframe not in self.subscription_map[epic]:
                return

            socket = self._find_socket_for(epic, timeframe)
            if not socket:
                return

            self.subscription_map[epic].remove(timeframe)
            self.socket_assignments[socket].remove((epic, timeframe))

        await socket.unsubscribe_from_epic(epic, timeframe)

        if not self.socket_assignments[socket]:
            await self._close_socket(socket)

    async def ping_all(self):
        for socket in list(self.sockets):
            try:
                await socket.ping_socket()
            except Exception:
                await self._force_close(socket)

    async def rebuild_all(self):
        """
        Full teardown + rebuild.
        Call this after auth refresh or systemic failure.
        """
        await Logger.app_log(
            title="SOCKET_REBUILD",
            message="Rebuilding all Capital sockets"
        )

        async with self.lock:
            subs = [
                (epic, tf)
                for epic, tfs in self.subscription_map.items()
                for tf in tfs
            ]

            self.subscription_map.clear()

            sockets = list(self.sockets)
            self.sockets.clear()
            self.socket_assignments.clear()

        for s in sockets:
            await s.close()

        for epic, tf in subs:
            await self.subscribe(epic, tf)

    # ───────────────────────────────
    # Internal helpers
    # ───────────────────────────────

    async def _get_or_create_socket(self) -> CapitalSocket:
        # reuse healthy sockets
        for s in self.sockets:
            if not s.connected:
                await self._force_close(s)
                continue

            if len(self.socket_assignments[s]) < self.MAX_SUBSCRIPTIONS_PER_SOCKET:
                return s

        # create new socket
        socket = CapitalSocket()
        await socket.connect_websocket()

        self.sockets.append(socket)
        self.socket_assignments[socket] = set()

        await Logger.app_log(
            title="SOCKET_NEW",
            message="New Capital socket created"
        )

        return socket

    async def _close_socket(self, socket: CapitalSocket):
        async with self.lock:
            if socket not in self.sockets:
                return

            await Logger.app_log(
                title="SOCKET_CLOSE",
                message="Closing idle socket"
            )

            await socket.close()

            self.sockets.remove(socket)
            self.socket_assignments.pop(socket, None)

    async def _force_close(self, socket: CapitalSocket):
        """
        Immediate close without caring about assignments.
        Used on fatal errors.
        """
        async with self.lock:
            if socket not in self.sockets:
                return

            await Logger.app_log(
                title="SOCKET_FORCE_CLOSE",
                message="Force closing broken socket"
            )

            await socket.close()

            self.sockets.remove(socket)
            self.socket_assignments.pop(socket, None)

    def _find_socket_for(self, epic: str, timeframe: str):
        for s, subs in self.socket_assignments.items():
            if (epic, timeframe) in subs:
                return s
        return None




# Example usage
capital_socket = CapitalSocketManager()


