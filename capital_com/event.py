


async def event_signal(ticker: str, timeframe: str):
    from enums.trade import TradeSide
    from hook import send_bulk_hook
    try:
        from capital_com.signal2 import signal_hybrid, signal_atr_breakout, signal_mean_reversion, signal_momentum, signal_trend_following, get_levels, signal_candle_patterns
        from capital_com.smc import signal_smc
        from capital_com.lit_snr import signal_lit_snr
        from leverage import get_leverage
        amount = 50
        # calculate profit and loss levels

        if timeframe == "DAY":
            side_mean_reversion = signal_mean_reversion(ticker, timeframe=timeframe)
            side_atr_breakout = signal_atr_breakout(ticker, timeframe=timeframe)
            side_smc = signal_smc(ticker, timeframe="HOUR_4")

            profit, loss = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=2)

            # ATR Breakout signals
            if side_atr_breakout != TradeSide.NEUTRAL and side_atr_breakout != side_smc:
                await send_bulk_hook(tickers=[ticker], hook_name="ATR BRK OUT", direction=side_atr_breakout, amount=amount, profit=profit, loss=loss, mkt_closed=True)

            # Mean Reversion signals
            if side_mean_reversion != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="MEAN REV", direction=side_mean_reversion, amount=amount, profit=profit, loss=loss, mkt_closed=True)
        
        
        
        elif timeframe == "HOUR":
            side_candle_patterns = signal_candle_patterns(ticker, timeframe="HOUR")

            profit, loss = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=3)

            # candle pattern signals
            if side_candle_patterns != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="CANDLE", direction=side_candle_patterns, amount=amount, profit=profit, loss=loss, mkt_closed=True)


        
        
        elif timeframe == "HOUR_4":
            side_smc = signal_smc(ticker, timeframe=timeframe)
            
            profit, loss = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=2)


            # SMC
            if side_smc != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="SMC", direction=side_smc, amount=amount, profit=profit, loss=loss, mkt_closed=True)
        


        elif timeframe == "MINUTE_30":
            side_lit_snr = signal_lit_snr(ticker=ticker, trigger_tf=timeframe, bias_tf="DAY", setup_tf="HOUR_4")

            profit, loss = get_levels(ticker, timeframe=timeframe, notional=amount * get_leverage(ticker), rr=4)


            # LIT SNR signals
            if side_lit_snr != TradeSide.NEUTRAL:
                await send_bulk_hook(tickers=[ticker], hook_name="LIT SNR", direction=side_lit_snr, amount=amount, profit=profit, loss=loss, mkt_closed=True)

    except Exception as e:
        print("Error in capital_com_signal:", str(e))
