


from capital_com.signal2 import signal_atr_breakout


async def event_signal(ticker: str, timeframe: str):
    from enums.trade import TradeSide
    from hook import send_hook, AsyncClient
    try:
        from capital_com.signal2 import signal_hybrid, signal_atr_breakout, signal_mean_reversion, signal_mean_reversion_v2, get_levels, signal_candle_patterns
        from capital_com.smc import signal_smc
        from capital_com.lit_snr import signal_lit_snr
        from leverage import get_leverage, get_instrument_type, EpicInstrument
        amount = 50 * get_leverage(ticker)
        # calculate profit and loss levels
        session = AsyncClient()

        if timeframe == "MINUTE_5":
            bias_tf = "HOUR" if EpicInstrument(ticker) == EpicInstrument.STOCKS else "HOUR_4"
            bias_signals = [
                signal_atr_breakout(ticker, timeframe=bias_tf),
                signal_mean_reversion(ticker, timeframe=bias_tf),
                signal_smc(ticker, timeframe=bias_tf)
            ]

            # pick bias direction if any bias gives a direction
            bias = pick_direction(bias_signals)
            if bias == TradeSide.NEUTRAL:
                return

            # execution signals on 5m
            exec_signals = [
                ("ATR BRK OUT", signal_atr_breakout(ticker, timeframe="MINUTE_5")),
                ("MEAN REV",    signal_mean_reversion(ticker, timeframe="MINUTE_5")),
                ("SMC",         signal_smc(ticker, timeframe="MINUTE_5"))
            ]

            for name, exec_side in exec_signals:
                if exec_side == bias:
                    profit, loss, trail = get_levels(ticker, timeframe=timeframe, notional=amount, rr=3)
                    await send_hook(ticker=ticker, hook_name=name, direction=exec_side, amount=amount, profit=profit, loss=loss, trail_sl=trail, session=session, mkt_closed=True)
        


        elif timeframe == "MINUTE_30" and get_instrument_type(ticker) != EpicInstrument.STOCKS:
            side_lit_snr = signal_lit_snr(ticker=ticker, trigger_tf=timeframe, bias_tf="DAY", setup_tf="HOUR_4")
            profit, loss, trail = get_levels(ticker, timeframe=timeframe, notional=amount, rr=3)

            # LIT SNR signals
            if side_lit_snr != TradeSide.NEUTRAL:
                await send_hook(ticker=ticker, hook_name="LIT SNR", direction=side_lit_snr, amount=amount, profit=profit, loss=loss, trail_sl=trail, session=session, mkt_closed=True)

        await session.aclose()

    except Exception as e:
        print("Error in capital_com_signal:", str(e))




def pick_direction(signals):
    """
    Given a list of directional outputs (LONG / SHORT / NEUTRAL),
    return a single unified direction.
    Priority:
        1. If all agree → use that
        2. If majority agree → use majority
        3. If conflict / no majority → NEUTRAL
    """
    from enums.trade import TradeSide

    # Filter out neutral values
    dirs = [s for s in signals if s is not None and s != TradeSide.NEUTRAL]

    if not dirs:
        return TradeSide.NEUTRAL

    # Count votes
    long_count = dirs.count(TradeSide.LONG)
    short_count = dirs.count(TradeSide.SHORT)

    if long_count > short_count:
        return TradeSide.LONG
    elif short_count > long_count:
        return TradeSide.SHORT
    else:
        # No majority → stand down
        return TradeSide.NEUTRAL

