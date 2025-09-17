from enum import Enum


class EpicInstrument(Enum):
    CRYPTO = "crypto"
    STOCKS = "stocks"        # indices, ETFs
    INDICES = "indices"  # treated as stocks
    COMMODITIES = "commodities"
    CURRENCIES = "currencies"  # forex

LEVERAGE = {
    EpicInstrument.CRYPTO: 20,
    EpicInstrument.CURRENCIES: 100,
    EpicInstrument.STOCKS: 20,
    EpicInstrument.COMMODITIES: 100,
    EpicInstrument.INDICES: 100
}


def get_instrument_type(epic: str) -> EpicInstrument:
    epic = epic.upper()

    # Group definitions
    forex_pairs = {
        "EURUSD", "USDJPY", "GBPUSD", "USDCAD", "AUDUSD",
        "USDCHF", "USDCNY", "USDMXN", "GBPAUD", "CADJPY",
        "USDZAR", "USDTRY", "AUDJPY", "NZDJPY"
    }
    cryptos = {"BTCUSD", "ETHUSD"}
    indices = {"QQQ", "SPY", "IWM", "VOO", "US100", "US500", "US30"}
    commodities = {"GOLD", "SILVER", "OIL_CRUDE", "OIL_BRENT", "NATGAS"}

    if epic in forex_pairs:
        return EpicInstrument.CURRENCIES
    if epic in cryptos:
        return EpicInstrument.CRYPTO
    if epic in indices:
        return EpicInstrument.INDICES
    if epic in commodities:
        return EpicInstrument.COMMODITIES
    return EpicInstrument.STOCKS


def get_leverage(epic: str) -> list[int]:
    instrument_type = get_instrument_type(epic)
    return LEVERAGE.get(instrument_type, 20)



# print(get_leverage("US100"))  # Output: EpicInstrument.CRYPTO