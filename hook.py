from httpx import AsyncClient
from enums.trade import TradeSide
import asyncio

memory = {}


async def send_hook(ticker: str,  hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int, session: AsyncClient):
    from settings import settings
    ticker = settings.ticker_mask(ticker)
        
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
            "TP", "SL", "MKT_CLOSED"
        ]
    }
    res = await session.post(url, json=payload)
    print(f"Hook sent for {ticker}: {res.status_code} - {res.text}")


async def send_bulk_hook(tickers: list, hook_name: str, direction: TradeSide, amount: int, profit: int, loss: int):
    async with AsyncClient() as session:
        # Create a list of tasks to send hooks concurrently
        tasks = [
            send_hook(ticker, hook_name, direction, amount, profit, loss, session)
            for ticker in tickers
        ]
        # Use asyncio.gather to run all tasks concurrently
        for i in range(0, len(tasks), 10):
            await asyncio.gather(*tasks[i:i+10])
    