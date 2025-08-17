from fastapi import FastAPI
from settings import settings
from asyncio import sleep, create_task
from enums.trade import TradeTimeFrame, TradeSide
from hook import send_bulk_hook

app = FastAPI()


async def crypto_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.crypto.ema import double_ema_list

    while True:
        long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
        # long_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.LONG)
        # long = [ticker for ticker in long if ticker in long_base]
        await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=55, loss=15)

        short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
        # short_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.SHORT)
        # short = [ticker for ticker in short if ticker in short_base]
        await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=55, loss=15)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration


async def stocks_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.stocks.ema import double_ema_list

    while True:
        long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
        # long_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.LONG)
        # long = [ticker for ticker in long if ticker in long_base]
        await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=51, loss=15)

        short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
        # short_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.SHORT)
        # short = [ticker for ticker in short if ticker in short_base]
        await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=51, loss=15)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration


async def etf_ema_monitor(timeframe: TradeTimeFrame):
    from screeners.etfs.ema import double_ema_list

    while True:
        long = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.LONG)
        # long_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.LONG)
        # long = [ticker for ticker in long if ticker in long_base]
        await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=51, loss=15)

        short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
        # short_base = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.FIVE_MIN, side=TradeSide.SHORT)
        # short = [ticker for ticker in short if ticker in short_base]
        await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=51, loss=15)

        await sleep(timeframe.timeframe_sleep() / 2)  # Sleep for the specified timeframe duration

@app.on_event("startup")
async def startup_event():
    # print(settings.watchlist)
    create_task(crypto_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")