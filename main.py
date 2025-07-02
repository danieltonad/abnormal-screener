from fastapi import FastAPI
from settings import settings
from asyncio import sleep, create_task
from enums.trade import TradeTimeFrame, TradeSide
from hook import send_bulk_hook

app = FastAPI()


async def crypto_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.crypto.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        await send_bulk_hook(tickers=long, hook_name="10/20 EMA", direction=TradeSide.SHORT, amount=50, profit=50, loss=11)

        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        await send_bulk_hook(tickers=short, hook_name="10/20 EMA", direction=TradeSide.LONG, amount=50, profit=50, loss=11)

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration


async def stocks_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.stocks.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        await send_bulk_hook(tickers=long, hook_name="10/20 EMA", direction=TradeSide.SHORT, amount=50, profit=50, loss=11)

        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        await send_bulk_hook(tickers=short, hook_name="10/20 EMA", direction=TradeSide.LONG, amount=50, profit=50, loss=11)

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration


async def etf_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.etfs.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        await send_bulk_hook(tickers=long, hook_name="10/20 EMA", direction=TradeSide.SHORT, amount=50, profit=50, loss=25)

        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        await send_bulk_hook(tickers=short, hook_name="10/20 EMA", direction=TradeSide.LONG, amount=50, profit=50, loss=25)

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration

@app.on_event("startup")
async def startup_event():
    # print(settings.watchlist)
    create_task(crypto_ema_monitor(TradeTimeFrame.FIFTEEN_MIN))
    create_task(stocks_ema_monitor(TradeTimeFrame.FIFTEEN_MIN))
    create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")