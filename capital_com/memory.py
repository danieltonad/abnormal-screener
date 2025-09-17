from settings import settings
from httpx import AsyncClient
from logger import Logger
import json, asyncio
from typing import Dict, Tuple, Deque
from collections import defaultdict, deque



class Memory:
    capital_auth_header: dict = {}
    # Latest OHLC per (epic, resolution)
    ohlc_latest: Dict[Tuple[str, str], dict] = {}

    # Rolling store: (epic, resolution) -> deque of bars
    ohlc_history: Dict[Tuple[str, str], Deque[dict]] = defaultdict(lambda: deque(maxlen=500))

    def update_ohlc_data(self, epic: str, resolution: str, timestamp: str, open: float, high: float, low: float, close: float, price_type: str):
        """Update OHLC data (latest + history) for an epic/resolution."""
        key = (epic, resolution)

        bar = {
            "t": timestamp,
            "o": open,
            "h": high,
            "l": low,
            "c": close,
            "price_type": price_type,
        }
        # print(f"OHLC Update for {epic} at {resolution}: {bar}")

        # Store latest
        self.ohlc_latest[key] = bar

        # Append to rolling history
        self.ohlc_history[key].append(bar)

    def get_latest(self, epic: str, resolution: str) -> dict:
        """Get latest OHLC for an epic/resolution."""
        return self.ohlc_latest.get((epic, resolution), {})

    def get_history(self, epic: str, resolution: str, n: int = 100) -> list:
        """Get last n bars for an epic/resolution."""
        return list(self.ohlc_history[(epic, resolution)][-n:])

    async def update_auth_header(self) -> None:
        try:
            payload = json.dumps({
            "identifier": settings.CAPITAL_IDENTITY,
            "password": settings.CAPITAL_PASSWORD,
            "encryptedPassword": False
            })
            headers = {
                'X-CAP-API-KEY': settings.CAPITAL_API_KEY,
                'Content-Type': 'application/json'
            }
            async with AsyncClient() as session:
                response = await session.post(f"https://api-capital.backend-capital.com/api/v1/session", headers=headers, data=payload)
            # print(response.status_code ,response.json())
            header: dict = response.headers
            CST = header.get("CST")
            X_SECURITY_TOKEN = header.get("X-SECURITY-TOKEN")
            # print(CST, X_SECURITY_TOKEN)
            self.capital_auth_header = {'X-SECURITY-TOKEN': X_SECURITY_TOKEN, 'CST': CST}
            # print("Capital.com Auth Header Updated")
            
        except Exception as e:
            await Logger.app_log(title="UPDATE_AUTH_HEADER_ERR", message=str(e))
            await asyncio.sleep(100)
            return await self.update_auth_header()


    
    

memory = Memory()