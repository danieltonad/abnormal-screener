from enums.trade import TradeTimeFrame, TradeSide
from settings import settings
from logger import Logger
import json


def double_ema_paylod(left: int, right: int, timeframe: TradeTimeFrame, operation: str = "crosses"):
    return json.dumps({"filter":[{"left":f"EMA{left}{timeframe.timeframe_period()}","operation": operation, "right":f"EMA{right}{timeframe.timeframe_period()}"}],"ignore_unknown_fields":False,"options":{"lang":"en"},"range":[0,10000],"sort":{"sortBy":"aum","sortOrder":"desc"},"symbols":{},"markets":["america"],"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etn"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etf"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"structured"}}]}}]}}]}})
    
async def double_ema_list(left: int, right: int, timeframe: TradeTimeFrame, side: TradeSide):
    operation = "crosses_above" if side == TradeSide.LONG else "crosses_below" if side == TradeSide.SHORT else ""
    return await __response_list(payload=double_ema_paylod(left, right, timeframe, operation))

async def __response_list(payload):
    try:
        res = await settings.SESSION.post(url=settings.ETF_SCREENER_URL, data=payload)
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

