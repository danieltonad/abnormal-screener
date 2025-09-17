from fastapi import FastAPI
from capital_com import memory
from capital_com.signals import signal_ema_crossover
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


async def capital_com_signal():
    from capital_com.signals import signal_ema_crossover, signal_rejection, signal_breakout
    from capital_com.smc import signal_smc, memory
    from leverage import get_leverage
    amount = 50
    
    while True: 
        for ticker in settings.capital_list:
            capital = get_leverage(ticker) * amount
            side_ema = signal_ema_crossover(ticker, timeframe="MINUTE")
            side_rej = signal_rejection(ticker, timeframe="MINUTE")
            side_bk = signal_breakout(ticker, timeframe="MINUTE")
            side_smc = signal_smc(ticker, timeframe="MINUTE_15")

            # EMA crossover signals
            if side_ema != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="5/13 EMA", direction=side_ema, amount=amount, profit=50, loss=50, mkt_closed=True)

            # Rejection and Breakout signals
            if side_rej != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="SR REJCT", direction=side_rej, amount=amount, profit=50, loss=50, mkt_closed=True)

            if side_bk != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="BRK OUT", direction=side_bk, amount=amount, profit=50, loss=50, mkt_closed=True)

            if side_smc != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="SMC", direction=side_smc, amount=amount, profit=50, loss=50, mkt_closed=True)

        await sleep(55)
        # msg = ""
        # for key, bars in memory.ohlc_history.items():
        #     msg += f"{key[0]} ({key[1]}): {len(bars)} bars\n"
        # print("OHLC Data Summary:\n", msg)

@app.on_event("startup")
async def startup_event():
    from jobs import JobManager
    
    await JobManager.start()
    # print(settings.watchlist)
    # create_task(crypto_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    # create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(capital_com_signal())


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")