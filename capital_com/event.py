from datetime import datetime, time


def is_trading_session() -> bool:
    now = datetime.utcnow().time()

    london_core = time(7, 30) <= now <= time(10, 30)
    ny_continuation = time(13, 30) <= now <= time(15, 30)

    transition_blackout = time(15, 45) <= now <= time(17, 15)

    return (london_core or ny_continuation) and not transition_blackout


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
    from capital_com.signal2 import TradeSide, signal_atr_breakout_exit, signal_atr_momentum, get_trail_amount_usd
    try:

        session = AsyncClient()

        if get_instrument_type(ticker) != EpicInstrument.CRYPTO and not is_trading_session():
            return


        if timeframe == "MINUTE_30":
            amount = 10
            profit, loss, trail_sl = amount, amount*2, amount
            atr_side_trend = signal_atr_breakout_exit(ticker=ticker, timeframe=timeframe)
            if atr_side_trend != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="TREND", direction=atr_side_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True)
            
        
        if timeframe == "MINUTE_15":
            amount = 5
            profit, loss, trail_sl = amount, amount*2, amount
            mommentum_trend = signal_atr_momentum(ticker=ticker, timeframe=timeframe)
            if mommentum_trend != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="MOMENTUM", direction=mommentum_trend, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session, strategy=True)



        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()
# todo -- asset based trailing (volatility bit)


