from httpx import AsyncClient
from enums.trade import TradeSide, TradeMode
import asyncio, random
from datetime import datetime


class Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"
    GRAY = "\033[90m"
    RED = "\033[91m"
    YELLOW = "\033[93m"

async def send_hook(ticker: str,  hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int, trail_sl: int, trade_mode: TradeMode, session: AsyncClient, mkt_closed: bool = False, recalibrate: bool = True, strategy: bool = False):
    from settings import settings
    ticker = settings.ticker_mask(ticker)
    if ticker not in settings.watchlist:
        return
    
    # gold exception 
    # if ticker == "GOLD":
    #     loss = 2 * loss
    
    url = "http://127.0.0.1:3556/webhook/trading-view"
    payload = {
        "epic": ticker,
        "direction": direction.value,
        "amount": int(amount),
        "hook_name": hook_name,
        "profit": int(profit),
        "loss": int(loss),
        "trail_sl": int(trail_sl),
        "exit_criteria": [
        "SL"
        ],
        "trade_mode": trade_mode.value
    }
    if mkt_closed:
        payload["exit_criteria"].append("EOW_CLOSE")
    if recalibrate:
        payload["exit_criteria"].append("RECALIBRATE")
    if strategy:
        payload["exit_criteria"].append("STRATEGY")
    await asyncio.sleep(random.uniform(0.1, 2.0))
    res = await session.post(url, json=payload)
    time = datetime.now().strftime("%I:%M:%S %p")
    if direction == TradeSide.LONG:
        direction = f"{Colors.GREEN}{direction.value}{Colors.RESET}"
    elif direction == TradeSide.SHORT:
        direction = f"{Colors.RED}{direction.value}{Colors.RESET}"
    elif direction == TradeSide.EXIT_LONG:
        direction = f"{Colors.CYAN}{direction.value}{Colors.RESET}"
    elif direction == TradeSide.EXIT_SHORT:
        direction = f"{Colors.YELLOW}{direction.value}{Colors.RESET}"
        
    
    print(f"[{time}]: {hook_name} Hook | {ticker}: {res.status_code} -> {direction}")


async def send_bulk_hook(tickers: list, hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int, mkt_closed: bool = False):
    async with AsyncClient() as session:
        for ticker in tickers:
            await send_hook(ticker, hook_name, direction, int(amount), int(profit), int(loss), session, mkt_closed)
            await asyncio.sleep(random.uniform(0.1, 2.0))