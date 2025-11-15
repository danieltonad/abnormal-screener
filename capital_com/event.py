


async def stocks_event_signal(ticker: str, timeframe: str):
    from enums.trade import TradeSide
    from hook import send_hook, AsyncClient
    try:
        from capital_com.signal2 import  get_levels, signal_unified
        from capital_com.smc import signal_smc
        from leverage import get_leverage, get_instrument_type, EpicInstrument
        
        amount = 50
        session = AsyncClient()

        if timeframe == "HOUR_4" and get_instrument_type(ticker) in [EpicInstrument.STOCKS, EpicInstrument.CRYPTO]:
            
            side_unified = signal_unified(ticker, timeframe=timeframe)
            side_smc = signal_smc(ticker, timeframe=timeframe)
            profit, loss, trail_sl = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=3, atr_mult=1)

            # volatility-adaptive, dual-regime system
            if side_unified != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="UNIFIED", direction=side_unified, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

            # SMC
            if side_smc != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="SMC", direction=side_smc, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)   


        await session.aclose()

    except Exception as e:
        print("STOCKS_SIGNAL_ERR:", str(e))
        await session.aclose()





async def faster_event_signal(ticker: str, timeframe: str):
    from hook import send_hook, AsyncClient
    from leverage import get_leverage, get_instrument_type, EpicInstrument
    from capital_com.signal2 import get_levels, TradeSide
    from capital_com.lit_snr import signal_lit_snr
    from .intra_day import signal_regime_adaptive_scalper
    try:

        # early exit stocks
        if get_instrument_type(ticker) == EpicInstrument.STOCKS:
            return
        
        session = AsyncClient()
        amount = 50

        if timeframe == "MINUTE_5" and get_instrument_type(ticker) in [EpicInstrument.CRYPTO, EpicInstrument.INDICES, EpicInstrument.COMMODITIES, EpicInstrument.CURRENCIES]:
            profit, loss, trail_sl = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=3)

            # INTRA-DAY REGIME ADAPTIVE SCALPER
            side_regime_scalper = signal_regime_adaptive_scalper(ticker=ticker, timeframe=timeframe)
            if side_regime_scalper != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="REGIME SCALP", direction=side_regime_scalper, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

            
            # LIT SNR signals
            side_lit_snr = signal_lit_snr(ticker=ticker, trigger_tf=timeframe, bias_tf="HOUR_4", setup_tf="HOUR")
            if side_lit_snr != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="LIT SNR", direction=side_lit_snr, amount=amount, profit=profit, loss=loss, trail_sl=trail_sl, mkt_closed=True, session=session)

        await session.aclose()

    except Exception as e:
        print("INTRA_DAY_ERR:", str(e))
        await session.aclose()
