from datetime import datetime, time
from enums.trade import TradeMode
from settings import settings


TDV_MINUTES_BUFFER = 30

def is_trading_session() -> bool:
    now = datetime.utcnow().time()

    london_core = time(7, 30) <= now <= time(10, 30)
    ny_continuation = time(13, 30) <= now <= time(15, 30)

    transition_blackout = time(15, 45) <= now <= time(17, 15)

    return (london_core or ny_continuation) and not transition_blackout




async def faster_event_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from leverage import get_leverage, get_instrument_type, EpicInstrument
    from capital_com.signal2 import TradeSide, signal_atr_breakout_exit, signal_atr_momentum
    try:

        session = AsyncClient()

        happen = get_instrument_type(ticker) != EpicInstrument.CRYPTO and not is_trading_session() and settings.TDV_NEXT_EVENT_MINUTES < TDV_MINUTES_BUFFER and settings.LAST_EVENT and settings.is_within_minutes_range(settings.LAST_EVENT, TDV_MINUTES_BUFFER)


        if timeframe == "MINUTE_30":
            amount = 8
            profit, loss, trail_sl = amount, amount, amount
            atr_side_trend = signal_atr_breakout_exit(ticker=ticker, timeframe=timeframe)
            if atr_side_trend != TradeSide.NEUTRAL:
                if happen and atr_side_trend in [TradeSide.LONG, TradeSide.SHORT]:
                    # print(f"Skipping {ticker} on {timeframe} due to market being closed.")
                    pass
                else:
                    await send_hook(ticker=ticker, hook_name="TREND", direction=atr_side_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.LIVE)
            
        
        if timeframe == "MINUTE_15":
            amount = 4
            profit, loss, trail_sl = amount, amount, amount
            mommentum_trend = signal_atr_momentum(ticker=ticker, timeframe=timeframe)
            if mommentum_trend != TradeSide.NEUTRAL:
                if happen and mommentum_trend in [TradeSide.LONG, TradeSide.SHORT]:
                    # print(f"Skipping {ticker} on {timeframe} due to market being closed.")
                    pass
                else:
                    await send_hook(ticker=ticker, hook_name="MOMENTUM", direction=mommentum_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True, trade_mode=TradeMode.LIVE)



        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()
# todo -- asset based trailing (volatility bit)


