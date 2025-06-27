from fastapi import FastAPI
from settings import settings

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    from enums.trade import TradeTimeFrame, TradeSide
    from screeners.crypto.ema import double_ema_list
    from screeners.crypto.reversal import reversal_list

    # long = await double_ema_list(left=5, right=10, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)
    # short = await double_ema_list(left=5, right=10, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.SHORT)
    # print(f"LONG EMA List: {long} \n\n")
    # print(f"SHORT EMA List: {short}")

    long = await reversal_list(timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)
    short = await reversal_list(timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.SHORT)
    print(f"LONG EMA List: {long} \n\n")
    print(f"SHORT EMA List: {short}")


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")