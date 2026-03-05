from fastapi import FastAPI
from settings import settings
from asyncio import sleep, create_task
from enums.trade import TradeTimeFrame, TradeSide
from datetime import datetime, timedelta, timezone

app = FastAPI()


def stocks_operation_time() -> bool:
    # Standard US stock market hours: 14:30 to 21:00 UTC (9:30am to 4:00pm EST), Monday to Friday
    now_utc = datetime.now(timezone.utc)
    is_weekday = now_utc.weekday() < 5  # 0=Monday, 4=Friday
    market_open = (
        is_weekday and
        now_utc.time() >= datetime.strptime("13:30", "%H:%M").time() and
        now_utc.time() <= datetime.strptime("20:00", "%H:%M").time()
    )
    # print(market_open)
    return market_open



@app.on_event("startup")
async def startup_event():
    from jobs import JobManager
    
    await JobManager.start()


@app.on_event("shutdown")
async def shutdown_event():
    await settings.SESSION.aclose()
    print("Session closed.")