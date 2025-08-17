import asyncio
from enums.trade import TradeTimeFrame, TradeSide

async def main():
    from screeners.crypto.ema import double_ema_list
    from screeners.stocks.ema import double_ema_list
    # from screeners.etfs.ema import double_ema_list
    resp = await double_ema_list(left=9, right=21, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)
    print(resp)


if __name__ == "__main__":
    asyncio.run(main())