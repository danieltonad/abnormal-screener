from enums.trade import TradeTimeFrame, TradeSide
from settings import settings
from logger import Logger
import json


def double_ema_paylod(left: int, right: int, timeframe: TradeTimeFrame, operation: str = "crosses"):
    change = 0.5 if operation == "crosses_above" else -0.5
    change_ops = "greater" if operation == "crosses_above" else "less"
    return json.dumps({"filter":[{"left":f"EMA{left}{timeframe.timeframe_period()}","operation": operation,"right":f"EMA{right}{timeframe.timeframe_period()}"},{"left": "change", "operation": change_ops, "right": change},{"left": "relative_volume_10d_calc", "operation": "greater", "right": 1.2},{"left": "market_cap_calc", "operation": "greater", "right": 10000000},{"left":"currency","operation":"equal","right": settings.CRYPTO_PAIR}],"options":{"lang":"en"},"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"expression":{"left":"type","operation":"in_range","right":["spot"]}}]}}]},"markets":["crypto"],"symbols":{"query":{"types":[]},"tickers":[]},"columns":["base_currency_logoid","currency_logoid"],"range":[0,10000]})

async def double_ema_list(left: int, right: int, timeframe: TradeTimeFrame, side: TradeSide):
    operation = "crosses_above" if side == TradeSide.LONG else "crosses_below" if side == TradeSide.SHORT else ""
    return await __response_list(payload=double_ema_paylod(left, right, timeframe, operation))

async def __response_list(payload):
    try:
        res = await settings.SESSION.post(url=settings.CRYPTO_SCREENER_URL, data=payload)
        if res.status_code != 200:
            return []
        result: dict = res.json()
        assets = []
        for dt in result.get("data"):
            exchange, ticker = (dt.get("s", "").split(":"))
            if "." not in ticker:
                assets.append(ticker)
        return list(set(assets) - settings.crypto_stable_symbol_list())
    except Exception as err:
        await Logger.app_log(title="CRYPTO_EMA_LIST_ERR", message=str(err))
        return []

