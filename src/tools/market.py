"""
Market Tools — yfinance, Finnhub, Alpha Vantage, price caching.

Multi-provider chain with fallback and TTL caching.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# In-memory price cache with TTL
_price_cache: dict[str, dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes for price data


def _get_cached_price(key: str) -> Optional[dict[str, Any]]:
    """Check cache for a price entry."""
    entry = _price_cache.get(key)
    if entry and (time.time() - entry["timestamp"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None


def _set_cached_price(key: str, data: dict[str, Any]) -> None:
    """Store price data in cache."""
    _price_cache[key] = {"data": data, "timestamp": time.time()}


# Commodity symbol mappings
COMMODITY_SYMBOLS = {
    "gold": {"yfinance": "GC=F", "finnhub": "OANDA:XAU_USD", "av": "GOLD"},
    "silver": {"yfinance": "SI=F", "finnhub": "OANDA:XAG_USD", "av": "SILVER"},
    "copper": {"yfinance": "HG=F", "finnhub": "OANDA:XCU_USD", "av": "COPPER"},
    "platinum": {"yfinance": "PL=F", "finnhub": "OANDA:XPT_USD", "av": "PLATINUM"},
    "palladium": {"yfinance": "PA=F", "finnhub": "OANDA:XPD_USD", "av": "PALLADIUM"},
}


async def yfinance_price(commodity: str, currency: str = "USD") -> dict[str, Any]:
    """
    Get commodity price from yfinance.
    Primary data source for commodity prices.
    """
    cache_key = f"yfinance_{commodity}_{currency}"
    cached = _get_cached_price(cache_key)
    if cached:
        return {**cached, "cached": True}

    symbol_map = COMMODITY_SYMBOLS.get(commodity.lower(), {})
    symbol = symbol_map.get("yfinance")

    if not symbol:
        return {"success": False, "error": f"Unknown commodity: {commodity}"}

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("regularMarketPrice") or info.get("previousClose")
        if not price:
            # Try fast_info
            price = ticker.fast_info.get("last_price", 0)

        if price:
            result = {
                "success": True,
                "commodity": commodity,
                "symbol": symbol,
                "price_usd": float(price),
                "currency": currency,
                "source": "yfinance",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _set_cached_price(cache_key, result)
            return result

        return {"success": False, "error": "Could not retrieve price from yfinance"}

    except ImportError:
        return {"success": False, "error": "yfinance not installed", "install": "pip install yfinance"}
    except Exception as e:
        return {"success": False, "error": f"yfinance error: {e}"}


async def finnhub_price(commodity: str) -> dict[str, Any]:
    """
    Get commodity price from Finnhub.
    Fallback data source.
    """
    cache_key = f"finnhub_{commodity}"
    cached = _get_cached_price(cache_key)
    if cached:
        return {**cached, "cached": True}

    api_key = os.environ.get("FINNHUB_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "FINNHUB_API_KEY not set"}

    symbol_map = COMMODITY_SYMBOLS.get(commodity.lower(), {})
    symbol = symbol_map.get("finnhub")

    if not symbol:
        return {"success": False, "error": f"Unknown commodity: {commodity}"}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": api_key},
            )
            resp.raise_for_status()
            data = resp.json()

        price = data.get("c", 0)  # Current price
        if price:
            result = {
                "success": True,
                "commodity": commodity,
                "symbol": symbol,
                "price_usd": float(price),
                "source": "finnhub",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            _set_cached_price(cache_key, result)
            return result

        return {"success": False, "error": "No price data from Finnhub"}

    except Exception as e:
        return {"success": False, "error": f"Finnhub error: {e}"}


async def alpha_vantage_price(commodity: str) -> dict[str, Any]:
    """
    Get commodity price from Alpha Vantage.
    Second fallback data source.
    """
    cache_key = f"av_{commodity}"
    cached = _get_cached_price(cache_key)
    if cached:
        return {**cached, "cached": True}

    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "ALPHA_VANTAGE_API_KEY not set"}

    symbol_map = COMMODITY_SYMBOLS.get(commodity.lower(), {})
    symbol = symbol_map.get("av")

    if not symbol:
        return {"success": False, "error": f"Unknown commodity: {commodity}"}

    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "COMMODITY_PRICE",
                    "symbol": symbol,
                    "apikey": api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Parse Alpha Vantage response
        price_data = data.get("data", [])
        if price_data:
            latest = price_data[0] if isinstance(price_data, list) else price_data
            price = latest.get("value", 0)

            if price:
                result = {
                    "success": True,
                    "commodity": commodity,
                    "symbol": symbol,
                    "price_usd": float(price),
                    "source": "alpha_vantage",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                _set_cached_price(cache_key, result)
                return result

        return {"success": False, "error": "No price data from Alpha Vantage"}

    except Exception as e:
        return {"success": False, "error": f"Alpha Vantage error: {e}"}


async def get_commodity_price_chain(commodity: str, currency: str = "USD") -> dict[str, Any]:
    """
    Get commodity price with multi-provider fallback chain.

    Chain: yfinance → Finnhub → Alpha Vantage → cached
    """
    # Try primary: yfinance
    result = await yfinance_price(commodity, currency)
    if result.get("success"):
        return result

    # Fallback 1: Finnhub
    result = await finnhub_price(commodity)
    if result.get("success"):
        return result

    # Fallback 2: Alpha Vantage
    result = await alpha_vantage_price(commodity)
    if result.get("success"):
        return result

    # All failed
    return {
        "success": False,
        "commodity": commodity,
        "error": "All price providers failed",
        "providers_tried": ["yfinance", "finnhub", "alpha_vantage"],
    }


async def price_history(
    commodity: str,
    period: str = "1y",
    interval: str = "1mo",
) -> dict[str, Any]:
    """Get historical price data from yfinance."""
    symbol_map = COMMODITY_SYMBOLS.get(commodity.lower(), {})
    symbol = symbol_map.get("yfinance")

    if not symbol:
        return {"success": False, "error": f"Unknown commodity: {commodity}"}

    try:
        import yfinance as yf

        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return {"success": False, "error": "No historical data available"}

        data_points = [
            {
                "date": str(idx.date()),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
            for idx, row in hist.iterrows()
        ]

        first_close = data_points[0]["close"] if data_points else 0
        last_close = data_points[-1]["close"] if data_points else 0
        change_pct = ((last_close - first_close) / first_close * 100) if first_close else 0

        return {
            "success": True,
            "commodity": commodity,
            "period": period,
            "interval": interval,
            "data_points": data_points,
            "summary": {
                "start_price": first_close,
                "end_price": last_close,
                "change_pct": round(change_pct, 2),
                "trend": "up" if change_pct > 5 else "down" if change_pct < -5 else "sideways",
            },
        }

    except ImportError:
        return {"success": False, "error": "yfinance not installed"}
    except Exception as e:
        return {"success": False, "error": f"History error: {e}"}


def register_market_tools(registry) -> None:
    """Register all market tools with the tool registry."""
    registry.register_handler("get_commodity_price", get_commodity_price_chain)
    registry.register_handler("get_price_history", price_history)
    registry.register_handler("yfinance_price", yfinance_price)
    registry.register_handler("finnhub_price", finnhub_price)
    registry.register_handler("alpha_vantage_price", alpha_vantage_price)
