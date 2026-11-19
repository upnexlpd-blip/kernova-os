"""Public spot market data. All prices and quote volumes are denominated in USDT."""
from dataclasses import dataclass
import json
import math
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://data-api.binance.vision/api/v3/"
PERIODS = {"24H": ("15m", 96), "7D": ("1h", 168), "30D": ("4h", 180)}


class MarketError(Exception):
    def __init__(self, message, retry_after=30):
        super().__init__(message)
        self.retry_after = retry_after


def request_json(path, **parameters):
    request = Request(BASE_URL + path + "?" + urlencode(parameters),
                      headers={"User-Agent": "Kernova-Crypto/0.1", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            data = response.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise MarketError("The provider response exceeded the supported size.")
        return json.loads(data)
    except HTTPError as error:
        retry_after = error.headers.get("Retry-After", "60")
        delay = min(max(int(retry_after), 60), 86400) if retry_after.isdigit() else 60
        if error.code in (418, 429):
            raise MarketError("The data provider requested a pause.", delay) from error
        raise MarketError(f"The data provider returned HTTP {error.code}.", 60) from error
    except (OSError, ValueError) as error:
        raise MarketError("Market data is unavailable. Check your internet connection.") from error


def finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite market value")
    return result


@dataclass(frozen=True)
class Ticker:
    symbol: str
    base: str
    price: float
    change: float
    volume: float
    high: float
    low: float
    at: int


def parse_tickers(payload, symbols):
    if not isinstance(payload, list):
        raise MarketError("The market snapshot was invalid.")
    result = []
    for item in payload:
        try:
            symbol = item["symbol"]
            if symbol not in symbols:
                continue
            row = Ticker(symbol, symbols[symbol], finite(item["lastPrice"]),
                         finite(item["priceChangePercent"]), finite(item["quoteVolume"]),
                         finite(item["highPrice"]), finite(item["lowPrice"]), int(item["closeTime"]))
            if row.price > 0 and row.volume >= 0 and row.high >= row.low > 0:
                result.append(row)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    if not result:
        raise MarketError("The provider returned no active USDT markets.")
    return sorted(result, key=lambda row: row.volume, reverse=True)


def exchange_symbols():
    payload = request_json("exchangeInfo", permissions="SPOT", symbolStatus="TRADING", showPermissionSets="false")
    try:
        symbols = {row["symbol"]: row["baseAsset"] for row in payload["symbols"]
                   if row["quoteAsset"] == "USDT" and row["status"] == "TRADING"
                   and row.get("isSpotTradingAllowed", True)}
        if not symbols:
            raise ValueError()
        return symbols
    except (KeyError, TypeError, ValueError) as error:
        raise MarketError("The exchange market list was invalid.") from error


def candles(symbol, period):
    interval, limit = PERIODS[period]
    payload = request_json("klines", symbol=symbol, interval=interval, limit=limit)
    try:
        rows = []
        for item in payload:
            at = int(item[0])
            open_, high, low, close, volume = map(finite, item[1:6])
            if not (at > 0 and high >= max(open_, close) and 0 < low <= min(open_, close) and volume >= 0):
                raise ValueError()
            rows.append((at, open_, high, low, close, volume))
        if len(rows) < 2 or any(a[0] >= b[0] for a, b in zip(rows, rows[1:])):
            raise ValueError()
        return rows
    except (TypeError, ValueError, IndexError) as error:
        raise MarketError("The chart response was invalid.") from error


def price(value):
    if 0 < value < .000001:
        return f"{value:.6g}"
    decimals = 2 if value >= 100 else 4 if value >= 1 else 8
    return f"{value:,.{decimals}f}"
