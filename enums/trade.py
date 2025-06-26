from enum import Enum

class TradeSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"  
    
    def inverse(self):
        if self == TradeSide.LONG:
            return TradeSide.SHORT
        elif self == TradeSide.SHORT:
            return TradeSide.LONG
        else:
            return TradeSide.NEUTRAL

class TradeTimeFrame(Enum):
    ONE_MIN = "1m"
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    THIRTY_MIN = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    ONE_DAY = "1d"
    ONE_WEEK = "1wk"
    ONE_MONTH = "1mo"
    NONE = ""
    # 
    @staticmethod
    def all():
        return [timeframe.value for timeframe in TradeTimeFrame if timeframe != TradeTimeFrame.NONE]
    
    def timeframe_period(self):
        timeframe_to_period = {
        TradeTimeFrame.ONE_MIN: "|1",
        TradeTimeFrame.FIVE_MIN: "|5",
        TradeTimeFrame.FIFTEEN_MIN: "|15",
        TradeTimeFrame.THIRTY_MIN: "|30",
        TradeTimeFrame.ONE_HOUR: "|60",
        TradeTimeFrame.TWO_HOURS: "|120",
        TradeTimeFrame.FOUR_HOURS: "|240",
        TradeTimeFrame.ONE_DAY: "",
        TradeTimeFrame.ONE_WEEK: '|1W',
        TradeTimeFrame.ONE_MONTH: '|1M'
        }
        return timeframe_to_period.get(self)