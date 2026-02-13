import os
from dotenv import load_dotenv
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta
from capital_com.news.main import TdvEventService




load_dotenv(override=True)


class Settings:
    news: TdvEventService = TdvEventService()
    def __init__(self):
        self.news = TdvEventService()
        self.TDV_EVENTS = []
        self.TDV_CLASSIFIED_EVENTS = []
        self.TDV_NEXT_EVENT_MINUTES = 999999
        self.LAST_EVENT = None
        from smart_group import conjured_epic_list
        if not os.path.exists("watchlist.txt"):
            self.watchlist = set()
        
        with open("watchlist.txt", "r") as f:
            self.watchlist = set(line.strip() for line in f if line.strip())
        
        with open("capital.txt", "r") as f:
            capital_list = set(line.strip() for line in f if line.strip())
            self.capital_list = conjured_epic_list(list(capital_list), block_size=8)
            print(self.capital_list)

        print(f"Watchlist loaded with {len(self.watchlist)} tickers.")
        print(f"Capital list loaded with {len(self.capital_list)} tickers.")



    CRYPTO_PAIR: str = "USD"
    CRYPTO_SCREENER_URL = "https://scanner.tradingview.com/crypto/scan?label-product=screener-crypto-cex"
    STOCKS_SCREENER_URL = "https://scanner.tradingview.com/america/scan?label-product=screener-stocks"
    ETF_SCREENER_URL = "https://scanner.tradingview.com/america/scan?label-product=screener-etf"
    TDV_SCREENER_HEADER: dict = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Cookie": os.getenv("TDV_COOKIE", ""),
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
        "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": "\"Windows\"",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
        "X-Language": "en",
        "X-Requested-With": "XMLHttpRequest"
    }

    SESSION: AsyncClient = AsyncClient(
        headers=TDV_SCREENER_HEADER,
        timeout=30.0,
        follow_redirects=True
    )

    CRYPTO_STABLE_COIN: list = ["USDT", "USDC", "DAI", "DIA","BUSD", "TUSD", "GUSD", "PAX", "FRAX", "MIM", "USTC", "LUSD", "USDP", "USDD", "EURS", "SUSD", "ALUSD", "CUSD", "USDE", "PYUSD", "SHILL", "USDY"]


    CAPITAL_IDENTITY: str = os.getenv("CAPITAL_IDENTITY")
    CAPITAL_PASSWORD: str = os.getenv("CAPITAL_PASSWORD")
    CAPITAL_API_KEY: str =  os.getenv("CAPITAL_API_KEY")
    
    
    def crypto_stable_symbol_list(self) -> set:
        return set([f"{coin}{self.CRYPTO_PAIR}" for coin in settings.CRYPTO_STABLE_COIN])
    
    def ticker_mask(self, ticker: str) -> str:
        tickers = {
            # Equity Index ETFs
            "SPY": "US500",       # S&P 500
            "QQQ": "US100",       # Nasdaq-100
            "DIA": "US30",        # Dow Jones

            # Commodity ETFs
            "GLD": "GOLD",        # Gold
            "SLV": "SILVER",      # Silver
            "USO": "OIL_CRUDE",         # WTI Crude Oil
            "BNO": "OIL_BRENT",       # Brent Crude Oil (United States Brent Oil Fund)
            "UNG": "NATGAS",      # Natural Gas
            "KOL": "1898",        
            "PKOL": "TECK",       
            "LIT": "LITHIUM",     # Lithium
            "URNM": "URANIUM",    # Uranium
            "CPER": "COPPER",     # Copper
            "PPLT": "PLATINUM",   # Platinum
            "PALL": "PALLADIUM",   # Palladium

            "FXE": "EURUSD",     # Euro
            "FXY": "USDJPY",     # Japanese Yen
            "FXB": "GBPUSD",     # British Pound
            "FXC": "USDCAD",     # Canadian Dollar
            "FXA": "AUDUSD",     # Australian Dollar
            "FXF": "USDCHF",     # Swiss Franc
            "CYB": "USDCNY",     # Chinese Yuan
            "FXM": "USDMXN",     # Mexican Peso
            # "UUP": "DXY",        # US Dollar Index (bullish)
            # "UDN": "DXY",  
        }
        return tickers.get(ticker, ticker)  # Default to the ticker itself if not found
    

    async def update_tdv_events(self):
        self.TDV_EVENTS = await self.news.get_events()
        print("TDV EVENTS => ", len(self.TDV_EVENTS))
    
    async def update_tdv_classified_events(self):
        self.TDV_CLASSIFIED_EVENTS = await self.news.get_classified_events()
        print("TDV CLASSIFIED EVENTS => ", len(self.TDV_CLASSIFIED_EVENTS))
    
    def update_tdv_next_event_minute(self):
        current_index = 0
        for current_index, event in enumerate(self.TDV_EVENTS):
            minutes_left = self.news.minutes_left(event.get("date"))
            if 0 < minutes_left < self.TDV_NEXT_EVENT_MINUTES :
                self.TDV_NEXT_EVENT_MINUTES = minutes_left
                break
        else:
            self.TDV_NEXT_EVENT_MINUTES = 999999
            self.LAST_EVENT = self.TDV_EVENTS[current_index -1].get("date") if current_index > 0 else None
        print("TDV NEXT EVENT MINUTES => ", self.TDV_NEXT_EVENT_MINUTES)
        # print("TDV LAST EVENT => ", self.LAST_EVENT)


    def classified_event_today(self) -> bool:
        now = datetime.utcnow()
        today_str = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        for event in self.TDV_CLASSIFIED_EVENTS:
            event_date = event.get("date", "")
            if event_date.startswith(today_str):
                return True
        return False
    

    def is_within_minutes_range(self,minutes: int) -> bool:
        if not self.LAST_EVENT:
            return False
        given_time = datetime.fromisoformat(
            self.LAST_EVENT.replace("Z", "+00:00")
        )
        now = datetime.now(timezone.utc)

        range_end = given_time + timedelta(minutes=minutes)

        return now <= range_end





    
        

settings = Settings()
