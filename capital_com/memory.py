from settings import settings
from httpx import AsyncClient
from logger import Logger
import json, asyncio
from typing import Dict, Tuple, Deque
from collections import defaultdict, deque
from datetime import datetime, timezone



class Memory:
    capital_auth_header: dict = {}
    # Latest OHLC per (epic, resolution)
    ohlc_latest: Dict[Tuple[str, str], dict] = {}

    # Rolling store: (epic, resolution) -> deque of bars
    ohlc_history: Dict[Tuple[str, str], Deque[dict]] = defaultdict(lambda: deque(maxlen=500))


    @staticmethod
    def _parse_ts(ts):
        """
        Normalize timestamp to datetime for strict comparison.
        Supports both ISO8601 strings and Unix timestamps (ms or s).
        """
        from datetime import datetime, timezone

        try:
            # Numeric (epoch in ms or s)
            if isinstance(ts, (int, float)):
                # detect ms vs s by magnitude
                if ts > 1e12:  # milliseconds
                    ts /= 1000
                return datetime.fromtimestamp(ts, tz=timezone.utc)

            # String numeric (e.g. "1760616900000")
            if isinstance(ts, str) and ts.isdigit():
                ts = int(ts)
                if ts > 1e12:
                    ts /= 1000
                return datetime.fromtimestamp(ts, tz=timezone.utc)

            # ISO8601 string
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None


    @staticmethod
    def iso_to_unix_ms(ts_str: str) -> int:
        """
        Convert an ISO8601 timestamp like '2025-10-16T13:05:00'
        to a Unix timestamp in milliseconds (UTC).
        """
        # Parse the ISO string
        dt = datetime.fromisoformat(ts_str)

        # Assume it's UTC if no timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Convert to milliseconds since epoch
        return int(dt.timestamp() * 1000)

    def update_ohlc_data(self, epic: str, resolution: str, timestamp: str, open: float, high: float, low: float, close: float, price_type: str):
        """Update OHLC data (latest + history) for an epic/resolution."""
        if price_type.lower() != "bid":
            return  # Ignore other price types for consistency

        key = (epic, resolution)
        dq = self.ohlc_history[key]

        ts_obj = self._parse_ts(timestamp)
        if ts_obj is None:
            # Invalid timestamp format — skip
            print(f"Invalid timestamp: {timestamp}")
            return

        bar = {
            "t": timestamp,
            "ts": ts_obj,  # store parsed timestamp for future sorting/debug
            "o": float(open),
            "h": float(high),
            "l": float(low),
            "c": float(close),
            "price_type": "bid",
        }


        # --- Strict chronological logic ---
        if not dq:
            dq.append(bar)
        else:
            last_ts = dq[-1]["ts"]
            if ts_obj < last_ts:
                # Reject out-of-order bar
                return
            elif ts_obj == last_ts:
                # Replace existing bar (same candle timestamp)
                dq[-1] = bar
            else:
                dq.append(bar)

        # --- Update latest bar ---
        self.ohlc_latest[key] = bar

    def get_latest(self, epic: str, resolution: str) -> dict:
        """Get latest OHLC for an epic/resolution."""
        return self.ohlc_latest.get((epic, resolution), {})

    def get_history(self, epic: str, resolution: str, n: int = 100) -> list:
        """Get last n bars (chronological) for an epic/resolution."""
        bars = list(self.ohlc_history.get((epic, resolution), []))
        # safety sort (should already be ordered)
        bars.sort(key=lambda b: b["ts"])
        return bars[-n:]

    
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




    async def preload_history(self, epic: str, resolution: str = "DAY", n: int = 100):
        """
        Fetch last n OHLC bars from Capital.com REST API and store in history.
        Fully strict: chronological, deduped, bid-only, sets latest.
        """
        try:
            headers = {
                "X-CAP-API-KEY": settings.CAPITAL_API_KEY,
                "CST": self.capital_auth_header.get("CST", ""),
                "X-SECURITY-TOKEN": self.capital_auth_header.get("X-SECURITY-TOKEN", "")
            }

            url = (
                f"https://api-capital.backend-capital.com/api/v1/prices/"
                f"{epic}?resolution={resolution}&max={n}&pageNumber=1"
            )

            async with AsyncClient() as session:
                resp = await session.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            prices = data.get("prices", [])
            if not prices:
                return []

            # Some APIs return newest first — make sure oldest→newest
            prices.sort(key=lambda p: p["snapshotTimeUTC"])

            for p in prices:
                # Defensive parsing — skip incomplete data
                try:
                    t = p["snapshotTimeUTC"]
                    o = float(p["openPrice"]["bid"])
                    h = float(p["highPrice"]["bid"])
                    l = float(p["lowPrice"]["bid"])
                    c = float(p["closePrice"]["bid"])
                except (KeyError, TypeError, ValueError):
                    continue

                # Route through strict updater (keeps everything validated)
                self.update_ohlc_data(
                    epic=epic,
                    resolution=resolution,
                    timestamp=self.iso_to_unix_ms(t),
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    price_type="bid",
                )

            # Return clean chronological list
            # return self.get_history(epic, resolution, n)

        except Exception as e:
            await Logger.app_log(title="PRELOAD_HISTORY_ERR", message=f"{epic}: {str(e)}")
            await asyncio.sleep(5)
            return await self.preload_history(epic, resolution, n)



    
    

memory = Memory()