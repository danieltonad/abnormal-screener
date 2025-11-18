


async def stocks_event_signal(ticker: str, timeframe: str):
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
    from capital_com.signal2 import get_levels, TradeSide
    from .signals import signal_breakout, signal_rejection, ema_crossover
    from capital_com.lit_snr import signal_lit_snr
    try:

        # early exit stocks
        if get_instrument_type(ticker) == EpicInstrument.STOCKS:
            return
        
        session = AsyncClient()
        amount = 50

        if timeframe == "MINUTE" and get_instrument_type(ticker) in [EpicInstrument.CRYPTO, EpicInstrument.INDICES, EpicInstrument.COMMODITIES, EpicInstrument.CURRENCIES]:
            profit, loss, trail_sl = get_levels(ticker, timeframe="HOUR", notional=amount * get_leverage(ticker), rr=5)


            # core scalp
            if get_instrument_type(ticker) in [EpicInstrument.INDICES, EpicInstrument.COMMODITIES]:
                # EMA Crossover signals
                side_ema = ema_crossover(ticker=ticker, timeframe=timeframe, fast=10, slow=20, slow_trend=300)
                if side_ema != TradeSide.NEUTRAL:
                    await send_hook(ticker=ticker, hook_name="10/20/300", direction=side_ema, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

                # SNR Breakout signals
                side_breakout = signal_breakout(ticker=ticker, timeframe=timeframe)
                if side_breakout != TradeSide.NEUTRAL:
                    await send_hook(ticker=ticker, hook_name="BRK OUT", direction=side_breakout, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

                # SNR Breakout signals
                side_rejection = signal_rejection(ticker=ticker, timeframe=timeframe)
                if side_rejection != TradeSide.NEUTRAL:
                    await send_hook(ticker=ticker, hook_name="SNR", direction=side_rejection, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

            
            # LIT SNR signals
            side_lit_snr = signal_lit_snr(ticker=ticker, trigger_tf=timeframe, bias_tf="HOUR", setup_tf="MINUTE_15")
            if side_lit_snr != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="LIT SNR", direction=side_lit_snr, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()
