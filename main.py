from fastapi import FastAPI
from settings import settings
from asyncio import sleep, create_task
from enums.trade import TradeTimeFrame, TradeSide

app = FastAPI()


async def crypto_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.crypto.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        print(f"CRYPTO LONG EMA List: {long} \n\n")
        print(f"CRYPTO SHORT EMA List: {short}")

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration


async def stocks_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.stocks.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        print(f"STOCKS LONG EMA List: {long} \n\n")
        print(f"STOCKS SHORT EMA List: {short}")

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration


async def etf_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.etfs.ema import double_ema_list

    while True:
        long = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.LONG)
        short = await double_ema_list(left=10, right=20, timeframe=timeframe, side=TradeSide.SHORT)
        print(f"ETFS LONG EMA List: {long} \n\n")
        print(f"ETFS SHORT EMA List: {short}")

        await sleep(timeframe.timeframe_sleep())  # Sleep for the specified timeframe duration

@app.on_event("startup")
async def startup_event():
    create_task(crypto_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")