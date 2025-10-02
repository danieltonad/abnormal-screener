from httpx import AsyncClient
from enums.trade import TradeSide
import asyncio


async def send_hook(ticker: str,  hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int, session: AsyncClient, mkt_closed: bool = False):
    from settings import settings
    ticker = settings.ticker_mask(ticker)
    if ticker not in settings.watchlist:
        return
        
    direction = "BUY" if direction == TradeSide.LONG else "SELL"
    url = "http://127.0.0.1:3556/webhook/trading-view"
    payload = {
        "epic": ticker,
        "direction": direction,
        "amount": amount,
        "hook_name": hook_name,
        "profit": profit,
        "loss": loss,
        "exit_criteria": [
            "TP", "STRATEGY", "SL"
        ]
    }
    if mkt_closed:
        payload["exit_criteria"].append("MKT_CLOSED")
    res = await session.post(url, json=payload)
    print(f"{hook_name} Hook | {ticker}: {res.status_code} -> {direction} | TP: ${profit} | SL: ${loss}")


async def send_bulk_hook(tickers: list, hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int, mkt_closed: bool = False):
    async with AsyncClient() as session:
        for ticker in tickers:
            await send_hook(ticker, hook_name, direction, amount, profit, loss, session, mkt_closed)
            await asyncio.sleep(0.2)
