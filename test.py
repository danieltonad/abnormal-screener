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
    print(memory.capital_auth_header)



asyncio.run(socket_test())