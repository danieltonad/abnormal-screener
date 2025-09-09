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
            await send_bulk_hook(tickers=long, hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=32, loss=7, mkt_closed=True)

            short = await double_ema_list(left=9, right=21, timeframe=timeframe, side=TradeSide.SHORT)
            await send_bulk_hook(tickers=short, hook_name="9/21 EMA", direction=TradeSide.SHORT, amount=50, profit=32, loss=7, mkt_closed=True)

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


async def capital_com_signal():
    from capital_com.signals import signal_ema_crossover, signal_rejection, signal_breakout
    from capital_com.smc import signal_smc
    
    for ticker in settings.capital_list:
        side_ema = signal_ema_crossover(ticker, fast=9, slow=21)
        side_rej = signal_rejection(ticker)
        side_bk = signal_breakout(ticker)
        side_smc = signal_smc(ticker)

        # Prioritize EMA crossover signals
        if side_ema != TradeSide.NEUTRAL:
            print("Capital.com Signal:", ticker, "EMA Crossover:", side_ema.name)
            await send_bulk_hook(tickers=[ticker], hook_name="9/21 EMA", direction=side_ema, amount=50, profit=25, loss=7)

        if side_rej != TradeSide.NEUTRAL:
            print("Capital.com Signal:", ticker, "SR REJECTION:", side_rej.name)
            await send_bulk_hook(tickers=[ticker], hook_name="SR REJECTION", direction=side_rej, amount=50, profit=25, loss=7)

        if side_bk != TradeSide.NEUTRAL:
            print("Capital.com Signal:", ticker, "BRK OUT:", side_bk.name)
            await send_bulk_hook(tickers=[ticker], hook_name="BRK OUT", direction=side_bk, amount=50, profit=25, loss=7)

        if side_smc != TradeSide.NEUTRAL:
            print("Capital.com Signal:", ticker, "SMC:", side_smc.name)
            await send_bulk_hook(tickers=[ticker], hook_name="SMC", direction=side_smc, amount=50, profit=25, loss=7)

    await sleep(10)  # Run every minute


@app.on_event("startup")
async def startup_event():
    from jobs import JobManager
    
    await JobManager.start()
    # print(settings.watchlist)
    create_task(crypto_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(capital_com_signal())


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")