import os
from dotenv import load_dotenv
load_dotenv(override=True)


class Settings:

    CRYPTO_SCREENER_URL = "https://api.binance.com/api/v3/klines"
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

settings = Settings()
