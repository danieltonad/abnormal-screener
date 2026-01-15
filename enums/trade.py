from enum import Enum

class TradeSide(Enum):
    LONG = "BUY"
    SHORT = "SELL"
    NEUTRAL = "NEUTRAL"  
    EXIT_LONG = "EXIT_BUY"
    EXIT_SHORT = "EXIT_SELL"
    

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
    
    def timeframe_sleep(self):
        timeframe_to_sleep = {
            TradeTimeFrame.ONE_MIN: 60,
            TradeTimeFrame.FIVE_MIN: 300,
            TradeTimeFrame.FIFTEEN_MIN: 900,
            TradeTimeFrame.THIRTY_MIN: 1800,
            TradeTimeFrame.ONE_HOUR: 3600,
            TradeTimeFrame.TWO_HOURS: 7200,
            TradeTimeFrame.FOUR_HOURS: 14400,
            TradeTimeFrame.ONE_DAY: 86400,
            TradeTimeFrame.ONE_WEEK: 604800,
            TradeTimeFrame.ONE_MONTH: 2592000
        }
        return timeframe_to_sleep.get(self, 60)