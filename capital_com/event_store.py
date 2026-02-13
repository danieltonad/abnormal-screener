
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple
from enum import Enum


class TradeSide(Enum):
    LONG = "BUY"
    SHORT = "SELL"
    NEUTRAL = "NEUTRAL"  
    EXIT_LONG = "EXIT_BUY"
    EXIT_SHORT = "EXIT_SELL"


@dataclass
class SignalLog:
    ticker: str
    hook_name: str
    timeframe: str
    side: TradeSide
    time: Optional[datetime] = None


class SignalStore:
    def __init__(self):
        self._data = {}

    def _key(self, signal: SignalLog):
        return (signal.ticker, signal.hook_name, signal.timeframe)

    def add_or_update(self, signal: SignalLog):
        key = self._key(signal)
        signal.time = signal.time or datetime.now(timezone.utc)
        self._data[key] = signal

    def get(self, ticker: str, hook_name: str, timeframe: str) -> Tuple[Optional[TradeSide], Optional[datetime]]:
        signal = self._data.get((ticker, hook_name, timeframe))
        if signal is None:
            return None, None
        return signal.side, signal.time

    def all(self):
        return list(self._data.values())
    




event_store = SignalStore()

# s1 = SignalLog("AAPL", "breakout", "1h", TradeSide.LONG)
# event_store.add_or_update(s1)

# # update
# s2 = SignalLog("AAPL", "breakout", "1h", TradeSide.SHORT)
# event_store.add_or_update(s2)

# print(event_store.get("AAPL", "breakout", "1h"))