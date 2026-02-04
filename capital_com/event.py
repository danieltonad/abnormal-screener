from datetime import datetime, time


def is_trading_session() -> bool:
    """Only trade during high-liquidity windows (UTC)."""
    now = datetime.utcnow().time()
    # Primary: London–NY overlap
    return time(12, 0) <= now <= time(16, 30)


async def mid_event_signal(ticker: str, timeframe: str):
    from enums.trade import TradeSide
    from hook import send_hook, AsyncClient
    try:
        from capital_com.signal2 import  signal_atr_breakout_exit
        from leverage import get_leverage, get_instrument_type, EpicInstrument
        
        amount = 50
        session = AsyncClient()

        await session.aclose()

    except Exception as e:
        print("STOCKS_SIGNAL_ERR:", str(e))
        await session.aclose()



async def faster_event_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from leverage import get_leverage, get_instrument_type, EpicInstrument
    from capital_com.signal2 import TradeSide, signal_atr_breakout_exit, signal_atr_hilo_breakout, signal_atr_momentum
    try:

        session = AsyncClient()


        if timeframe == "MINUTE_30":
            amount = 5
            profit, loss, trail_sl = amount*2, amount*2, amount//2
            # regime = signal_atr_hilo_breakout(ticker=ticker, timeframe="HOUR", ema_period=21, atr_period=14, atr_mult=1, swing_lookback=10)
            atr_side_trend = signal_atr_breakout_exit(ticker=ticker, timeframe=timeframe)
            # print(f"TREND_SIGNAL {ticker} {timeframe}: {atr_side_trend.value} -> regime: {regime.value}")
            if atr_side_trend != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="TREND", direction=atr_side_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True)

        
        if timeframe == "MINUTE_15":
            amount = 3
            profit, loss, trail_sl = amount*2, amount*2, amount//2
            # regime = signal_atr_breakout_exit(ticker=ticker, timeframe="MINUTE_30")
            mommentum_trend = signal_atr_momentum(ticker=ticker, timeframe=timeframe)
            if mommentum_trend != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="MOMENTUM", direction=mommentum_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True)



        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()



