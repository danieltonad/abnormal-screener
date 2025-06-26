from fastapi import FastAPI
from settings import settings

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    from enums.trade import TradeTimeFrame, TradeSide
    from screeners.crypto.ema import double_ema_list

    data = await double_ema_list(left=5, right=10, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.LONG)
    # data += await double_ema_list(left=5, right=10, timeframe=TradeTimeFrame.ONE_MIN, side=TradeSide.SHORT)
    print(f"Double EMA List: {data}")


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")