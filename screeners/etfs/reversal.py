from enums.trade import TradeTimeFrame, TradeSide
from settings import settings
from logger import Logger
import json


def reversal_bull_payload(timeframe: TradeTimeFrame):
    return json.dumps({"columns":[],"filter":[{"left":f"CCI20{timeframe.timeframe_period()}","operation":"eless","right":-100},{"left":f"MoneyFlow{timeframe.timeframe_period()}","operation":"eless","right":30},{"left":f"RSI{timeframe.timeframe_period()}","operation":"eless","right":30},{"left":f"W.R{timeframe.timeframe_period()}","operation":"eless","right":-80},{"left":f"Stoch.RSI.K{timeframe.timeframe_period()}","operation":"eless","right":20},{"left":f"Stoch.RSI.K{timeframe.timeframe_period()}","operation":"eless","right":20}],"ignore_unknown_fields":False,"options":{"lang":"en"},"range":[0,10000],"sort":{"sortBy":"aum","sortOrder":"desc"},"symbols":{},"markets":["america"],"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etn"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etf"]}}]}}, {"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"structured"}}]}}]}}]}})

def reversal_bear_payload(timeframe: TradeTimeFrame):
    return json.dumps({"columns":[],"filter":[{"left":f"RSI{timeframe.timeframe_period()}","operation":"egreater","right":70},{"left":"exchange","operation":"in_range","right":["AMEX","NASDAQ","NYSE"]},{"left":f"Stoch.K{timeframe.timeframe_period()}","operation":"egreater","right":80},{"left":f"Stoch.D{timeframe.timeframe_period()}","operation":"egreater","right":80},{"left":f"MoneyFlow|{timeframe.timeframe_period()}","operation":"egreater","right":70},{"left":f"CCI20{timeframe.timeframe_period()}","operation":"egreater","right":100},{"left":f"W.R{timeframe.timeframe_period()}","operation":"egreater","right":-20}],"ignore_unknown_fields":False,"options":{"lang":"en"},"range":[0,10000],"sort":{"sortBy":"aum","sortOrder":"desc"},"symbols":{},"markets":["america"],"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etn"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"typespecs","operation":"has","right":["etf"]}}]}}, {"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"structured"}}]}}]}}]}})
    
async def reversal_list(timeframe: TradeTimeFrame, side: TradeSide):
    if side == TradeSide.LONG:
        return await __response_list(payload=reversal_bull_payload(timeframe))
    elif side == TradeSide.SHORT:
        return await __response_list(payload=reversal_bear_payload(timeframe))
    else:
        return []


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
        await Logger.app_log(title="ETF_REVERSAL_LIST_ERR", message=str(err))
        return []

