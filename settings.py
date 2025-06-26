import os
from dotenv import load_dotenv
from httpx import AsyncClient

load_dotenv(override=True)


class Settings:
    CRYPTO_PAIR: str = "USD"
    CRYPTO_SCREENER_URL = "https://scanner.tradingview.com/crypto/scan?label-product=screener-crypto-cex"
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
    
    
    def crypto_stable_symbol_list(self) -> set:
        return set([f"{coin}{self.CRYPTO_PAIR}" for coin in settings.CRYPTO_STABLE_COIN])

settings = Settings()
