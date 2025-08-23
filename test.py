import asyncio


async def test_play():
    from screeners.etfs.ema import double_ema_list
    from enums.trade import TradeTimeFrame, TradeSide

    long = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)

    print("Long EMA List:", long)

    short = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.SHORT)

    print("Short EMA List:", short)

asyncio.run(test_play())