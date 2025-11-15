import os
from dotenv import load_dotenv
from httpx import AsyncClient

load_dotenv(override=True)


class Settings:

    def __init__(self):
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
    
        

settings = Settings()
