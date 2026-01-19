from fastapi import FastAPI
from settings import settings
from asyncio import sleep, create_task
from enums.trade import TradeTimeFrame, TradeSide
from hook import send_bulk_hook
from datetime import datetime, timedelta, timezone

app = FastAPI()


def stocks_operation_time() -> bool:
    # Standard US stock market hours: 14:30 to 21:00 UTC (9:30am to 4:00pm EST), Monday to Friday
    now_utc = datetime.now(timezone.utc)
    is_weekday = now_utc.weekday() < 5  # 0=Monday, 4=Friday
    market_open = (
        is_weekday and
        now_utc.time() >= datetime.strptime("13:30", "%H:%M").time() and
        now_utc.time() <= datetime.strptime("20:00", "%H:%M").time()
    )
    # print(market_open)
    return market_open


async def crypto_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.crypto.ema import double_ema_list

    while True:
        long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
        await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=25, loss=5)

        short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
        await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=25, loss=5)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration


async def stocks_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.stocks.ema import double_ema_list

    while True:
        if stocks_operation_time():

            long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
            await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=50, loss=50, mkt_closed=True)

            short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
            await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=50, loss=50, mkt_closed=True)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration


async def etf_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.etfs.ema import double_ema_list

    while True:
        if stocks_operation_time():

            long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
            await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=35, loss=7, mkt_closed=True)

            short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
            await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=35, loss=7, mkt_closed=True)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration


@app.on_event("startup")
async def startup_event():
    from jobs import JobManager
    
    await JobManager.start()
    # print(settings.watchlist)
    # create_task(crypto_ema_monitor(TradeTimeFrame.ONE_MIN))
    # create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    # create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))
    # await capital_com_signal()


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")