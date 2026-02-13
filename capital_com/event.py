import asyncio
from datetime import datetime, time, timezone
from enums.trade import TradeMode
from settings import settings
from .event_store import event_store, SignalLog


TDV_MINUTES_BUFFER = 30

def is_trading_session() -> bool:
    now = datetime.now(timezone.utc).time()

    london_core = time(7, 30) <= now <= time(10, 30)
    ny_continuation = time(13, 30) <= now <= time(15, 30)

    transition_blackout = time(15, 45) <= now <= time(17, 15)

    return (london_core or ny_continuation) and not transition_blackout


def same_minute(_time: datetime):
    return _time.strftime("%Y-%m-%d %H:%M") == datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")


async def faster_event_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from leverage import get_leverage, get_instrument_type, EpicInstrument
    from capital_com.signal2 import TradeSide, signal_atr_breakout_exit, signal_atr_momentum
    try:
        if ticker in ["GOLD", "SILVER"]:
            return
        session = AsyncClient()

        happen = get_instrument_type(ticker) != EpicInstrument.CRYPTO and not is_trading_session()
        news = settings.TDV_NEXT_EVENT_MINUTES < TDV_MINUTES_BUFFER or settings.is_within_minutes_range(TDV_MINUTES_BUFFER)


        
        if timeframe == "MINUTE_15":
            hook_name = "MOMENTUM"
            amount = 3
            profit, loss, trail_sl = amount, amount, amount//2
            mommentum_trend = signal_atr_momentum(ticker=ticker, timeframe=timeframe)
            if mommentum_trend != TradeSide.NEUTRAL:
                if happen and mommentum_trend in [TradeSide.LONG, TradeSide.SHORT]:
                    # print(f"Skipping {ticker} on {timeframe} due to market being closed.")
                    pass
                else:
                    if not news:
                        await send_hook(ticker=ticker, hook_name=hook_name, direction=mommentum_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.LIVE)
                        event_store.add_or_update(SignalLog(ticker=ticker, timeframe=timeframe, side=mommentum_trend, hook_name=hook_name))

        
        
        
        if timeframe == "MINUTE_30":
            hook_name = "TREND"
            amount = 6
            profit, loss, trail_sl = amount, amount, amount//2
            atr_side_trend = signal_atr_breakout_exit(ticker=ticker, timeframe=timeframe)
            if atr_side_trend != TradeSide.NEUTRAL:
                if happen and atr_side_trend in [TradeSide.LONG, TradeSide.SHORT]:
                    # print(f"Skipping {ticker} on {timeframe} due to market being closed.")
                    pass
                else:
                    if not news:
                        await asyncio.sleep(2)  # Small delay to ensure momentum signal is processed first
                        side, _time = event_store.get(ticker=ticker, timeframe=timeframe, hook_name="MOMENTUM")
                        if side == atr_side_trend and same_minute(_time):
                            pass
                        else:
                            await send_hook(ticker=ticker, hook_name=hook_name, direction=atr_side_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.LIVE)
                        
                        event_store.add_or_update(SignalLog(ticker=ticker, timeframe=timeframe, side=atr_side_trend, hook_name=hook_name))
            



        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()










async def gold_silver_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from capital_com.signal2 import TradeSide, signal_gold_intraday, signal_silver_intraday
    try:
        if ticker not in ["GOLD", "SILVER"]:
            return      

        session = AsyncClient()

        amount = 50
        profit, loss, trail_sl = amount, amount, amount
        min = "15" if timeframe == "MINUTE_15" else "30"
    
        gold_trend = signal_gold_intraday(ticker=ticker, timeframe=timeframe)
        if gold_trend != TradeSide.NEUTRAL:
            await send_hook(ticker=ticker, hook_name=f"SIG_{min}", direction=gold_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.DEMO)

        silver_trend = signal_silver_intraday(ticker=ticker, timeframe=timeframe)
        if silver_trend != TradeSide.NEUTRAL:
            await send_hook(ticker=ticker, hook_name=f"SIG_{min}", direction=silver_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.DEMO)

        await session.aclose()

    except Exception as e:
        print("GOLD_INTRADAY_ERR:", str(e))
        await session.aclose()


