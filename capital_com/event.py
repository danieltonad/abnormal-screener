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
        from capital_com.signal2 import  get_levels, signal_candle_patterns
        from capital_com.smc import signal_smc
        from leverage import get_leverage, get_instrument_type, EpicInstrument
        
        amount = 50
        session = AsyncClient()

        if timeframe == "HOUR" and get_instrument_type(ticker) == EpicInstrument.STOCKS:
            
            profit, loss, trail_sl = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=5)
            
            side_smc = signal_smc(ticker, timeframe=timeframe, confirmation_required=2)
            side_candle = signal_candle_patterns(ticker, trigger_timeframe="HOUR", confirmation_timeframe="DAY")

            # SMC
            if side_smc != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="SMC", direction=side_smc, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)   

            if side_candle != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="CANDLE", direction=side_candle, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)


        await session.aclose()

    except Exception as e:
        print("STOCKS_SIGNAL_ERR:", str(e))
        await session.aclose()



async def faster_event_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from leverage import get_leverage, get_instrument_type, EpicInstrument
    from capital_com.signal2 import get_levels, TradeSide, signal_trend_following
    try:
        print(f"Faster Event Signal Triggered: {ticker} | {timeframe}")

        session = AsyncClient()
        amount = 50
        profit, loss, trail_sl = 500, 500, 100

        if timeframe not in ["MINUTE_15"]:
            return


        side_trend = signal_trend_following(ticker=ticker, timeframe=timeframe)
        if side_trend != TradeSide.NEUTRAL:
            await send_hook(ticker=ticker, hook_name=f"{timeframe}", direction=side_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True)

        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()



