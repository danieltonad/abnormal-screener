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
    from capital_com.signal2 import signal_hybrid, signal_atr_breakout, signal_mean_reversion, signal_momentum, signal_trend_following, get_levels
    from capital_com.smc import signal_smc
    from leverage import get_leverage
    amount = 50
    
    while True: 
        for ticker in settings.capital_list:
            side_smc = signal_smc(ticker, timeframe="DAY")
            side_hybrid = signal_hybrid(ticker, timeframe="DAY")
            side_atr_breakout = signal_atr_breakout(ticker, timeframe="DAY")
            side_mean_reversion = signal_mean_reversion(ticker, timeframe="DAY")
            side_momentum = signal_momentum(ticker, timeframe="DAY")
            side_trend_following = signal_trend_following(ticker, timeframe="DAY")
            
            # calculate profit and loss levels
            profit_long, loss_long = get_levels(ticker, TradeSide.LONG, timeframe="DAY", rr=2, notional=amount * get_leverage(ticker))
            profit_short, loss_short = get_levels(ticker, TradeSide.SHORT, timeframe="DAY", rr=2, notional=amount * get_leverage(ticker))

            # SMC
            if side_smc != TradeSide.NEUTRAL:
                profit = profit_long if side_smc == TradeSide.LONG else profit_short
                loss = loss_long if side_smc == TradeSide.LONG else loss_short
                await send_bulk_hook(tickers=[ticker], hook_name="SMC", direction=side_smc, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # Hybrid signals
            if side_hybrid != TradeSide.NEUTRAL:
                profit = profit_long if side_hybrid == TradeSide.LONG else profit_short
                loss = loss_long if side_hybrid == TradeSide.LONG else loss_short
                await send_bulk_hook(tickers=[ticker], hook_name="HYBRID", direction=side_hybrid, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # ATR Breakout signals
            if side_atr_breakout != TradeSide.NEUTRAL:
                profit = profit_long if side_atr_breakout == TradeSide.LONG else profit_short
                loss = loss_long if side_atr_breakout == TradeSide.LONG else loss_short
                await send_bulk_hook(tickers=[ticker], hook_name="ATR BRK OUT", direction=side_atr_breakout, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # Mean Reversion signals
            if side_mean_reversion != TradeSide.NEUTRAL:
                profit = profit_long if side_mean_reversion == TradeSide.LONG else profit_short
                loss = loss_long if side_mean_reversion == TradeSide.LONG else loss_short
                await send_bulk_hook(tickers=[ticker], hook_name="MEAN REV", direction=side_mean_reversion, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # Momentum signals
            # if side_momentum != TradeSide.NEUTRAL:
            #     profit = profit_long if side_momentum == TradeSide.LONG else profit_short
            #     loss = loss_long if side_momentum == TradeSide.LONG else loss_short
            #     await send_bulk_hook(tickers=[ticker], hook_name="MOMENTUM", direction=side_momentum, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # Trend Following signals
            if side_trend_following != TradeSide.NEUTRAL:
                profit = profit_long if side_trend_following == TradeSide.LONG else profit_short
                loss = loss_long if side_trend_following == TradeSide.LONG else loss_short
                await send_bulk_hook(tickers=[ticker], hook_name="TREND", direction=side_trend_following, amount=amount, profit=profit, loss=loss, mkt_closed=True)

        await sleep(35)
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
    # create_task(stocks_ema_monitor(TradeTimeFrame.ONE_MIN))
    # create_task(etf_ema_monitor(TradeTimeFrame.ONE_MIN))
    create_task(capital_com_signal())


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")