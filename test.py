import asyncio
from enums.trade import TradeTimeFrame, TradeSide


async def test_play():
    # from screeners.etfs.ema import double_ema_list
    from screeners.crypto.ema import double_ema_list
    from hook import send_bulk_hook

    # long = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)

    # print("Long EMA List:", long)

    # short = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.SHORT)

    # print("Short EMA List:", short)

    await send_bulk_hook(tickers=["US100", "BTCUSD"], hook_name="9/21 EMA", direction=TradeSide.LONG, amount=50, profit=35, loss=7, mkt_closed=True)


# asyncio.run(test_play())




async def socket_test():
    from capital_com.socket import CapitalSocket, memory, Logger
    from capital_com.signals import signal_ema_crossover, signal_rejection, signal_breakout 
    from capital_com.smc import signal_smc

    await memory.update_auth_header()
    socket = CapitalSocket()
    await socket.connect_websocket()
    await socket.subscribe_to_epic("US100")
    # await socket.subscribe_to_epic("BTCUSD")
    # await socket.subscribe_to_epic("ETHUSD")
    # await socket.subscribe_to_epic("BNBUSD")
    
    count = 0
    while True:
        ticker = "US100"
        # ema_sig: TradeSide = signal_ema_crossover(ticker)
        # rej_sig: TradeSide = signal_rejection(ticker)
        # breakout_sig: TradeSide = signal_breakout(ticker)
        smc_sig: TradeSide = signal_smc(ticker)

        if smc_sig != TradeSide.NEUTRAL:
            await Logger.app_log(title="SMC_SIGNAL", message=f"{ticker} SMC Signal: {smc_sig.value}")

        # if ema_sig != TradeSide.NEUTRAL:
        #     await Logger.app_log(title="EMA_SIGNAL", message=f"{ticker} EMA Signal: {ema_sig.value}")
        # if rej_sig != TradeSide.NEUTRAL:
        #     await Logger.app_log(title="REJECTION_SIGNAL", message=f"{ticker} Rejection Signal: {rej_sig.value}")
        # if breakout_sig != TradeSide.NEUTRAL:
        #     await Logger.app_log(title="BREAKOUT_SIGNAL", message=f"{ticker} Breakout Signal: {breakout_sig.value}")
        
        # print(f"EMA: {ema_sig}, REJ: {rej_sig}, BO: {breakout_sig}", end="\r")
        print(f"SMC: {smc_sig}   - [{len(memory.ohlc_history.get((ticker, 'MINUTE'), []))}]", end="\r")

        await asyncio.sleep(5)
        count += 1
        if count % 25 == 0:
            await socket.ping_socket()



asyncio.run(socket_test())