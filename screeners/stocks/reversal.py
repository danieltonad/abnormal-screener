from enums.trade import TradeTimeFrame, TradeSide
from settings import settings
from logger import Logger
import json


def reversal_bull_payload(timeframe: TradeTimeFrame):
    timeframe_unit = timeframe.timeframe_period()
    return json.dumps({"filter":[{"left":f"RSI{timeframe_unit}","operation":"eless","right":30},{"left":f"Stoch.K{timeframe_unit}","operation":"eless","right":20},{"left":f"Stoch.D{timeframe_unit}","operation":"eless","right":20},{"left":f"CCI20{timeframe_unit}","operation":"eless","right":-100},{"left":f"Recommend.Other{timeframe_unit}","operation":"nequal","right":0.1},{"left":f"W.R{timeframe_unit}","operation":"eless","right":-80},{"left":"currency","operation":"equal","right":settings.CRYPTO_PAIR}],"options":{"lang":"en"},"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"expression":{"left":"type","operation":"in_range","right":["spot"]}}]}},{"operation":{"operator":"or","operands":[{"expression":{"left":f"Recommend.Other{timeframe_unit}","operation":"in_range","right":[0.1,0.5]}},{"expression":{"left":f"Recommend.Other{timeframe_unit}","operation":"in_range","right":[0.5,1]}}]}}]},"markets":["crypto"],"symbols":{"query":{"types":[]},"tickers":[]},"columns":[f"Recommend.All{timeframe_unit}"],"range":[1500]})

def reversal_bear_payload(timeframe: TradeTimeFrame):
    timeframe_unit = timeframe.timeframe_period()
    return json.dumps({"filter":[{"left":f"RSI{timeframe_unit}","operation":"egreater","right":70},{"left": f"Stoch.K{timeframe_unit}","operation":"egreater","right":80},{"left":f"Stoch.D{timeframe_unit}","operation":"egreater","right":80},{"left":f"CCI20{timeframe_unit}","operation":"egreater","right":100},{"left":f"W.R{timeframe_unit}","operation":"egreater","right":-20},{"left":"currency","operation":"equal","right":settings.CRYPTO_PAIR}],"options":{"lang":"en"},"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"expression":{"left":"type","operation":"in_range","right":["spot"]}}]}}]},"markets":["crypto"],"symbols":{"query":{"types":[]},"tickers":[]},"columns":[],"range":[0,1500]})
    
async def reversal_list(timeframe: TradeTimeFrame, side: TradeSide):
    if side == TradeSide.LONG:
        return await __response_list(payload=reversal_bull_payload(timeframe))
    elif side == TradeSide.SHORT:
        return await __response_list(payload=reversal_bear_payload(timeframe))
    else:
        return []


async def __response_list(payload):
    try:
        res = await settings.SESSION.post(url=settings.STOCKS_SCREENER_URL, data=payload)
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
        await Logger.app_log(title="STOCKS_REVERSAL_LIST_ERR", message=str(err))
        return []

