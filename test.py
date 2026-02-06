import asyncio
from enums.trade import TradeTimeFrame, TradeSide
from capital_com.event import is_trading_session

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
    from capital_com.socket import  memory
    from hook import send_hook, AsyncClient

    # await memory.update_auth_header()
    

    # from capital_com.socket_manager import capital_socket

    # await capital_socket.subscribe("US100", "MINUTE")

    # await memory.preload_history("US100", resolution="MINUTE", n=5)
    # print(memory.get_history(epic="US100", resolution="MINUTE"), end="\n\n\n")


    # while True:
    #     await asyncio.sleep(30)

    #     print(memory.get_history(epic="US100", resolution="MINUTE"), end="\n\n\n")
    #     await capital_socket.ping_all()
    # session = AsyncClient()
    # await send_hook(ticker="US30", hook_name="TEST SOCKET", direction=TradeSide.EXIT_LONG, amount=50, profit=25/2, loss=10, trail_sl=5, session=session)
    # await session.aclose()

    print(is_trading_session())




asyncio.run(socket_test())