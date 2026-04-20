# verilogos/application/sources/kucoin.py
"""KuCoin exchange data source (REST polling, public API)."""

from typing import List, Dict, Optional
import logging
import time

import aiohttp

from verilogos.application.models import MarketTick
from verilogos.application.sources.base import BaseSource

logger = logging.getLogger(__name__)

# KuCoin public API — no auth needed
_TICKERS_URL = "https://api.kucoin.com/api/v1/market/allTickers"

# Default symbol mapping: internal → KuCoin symbol
_DEFAULT_PAIRS: Dict[str, str] = {
    "BTCUSDT":  "BTC-USDT",
    "ETHUSDT":  "ETH-USDT",
    "XRPUSDT":  "XRP-USDT",
    "ADAUSDT":  "ADA-USDT",
    "DOTUSDT":  "DOT-USDT",
    "SOLUSDT":  "SOL-USDT",
    "AVAXUSDT": "AVAX-USDT",
    "MATICUSDT": "MATIC-USDT",
    "LINKUSDT": "LINK-USDT",
    "DOGEUSDT": "DOGE-USDT",
}


class KuCoinSource(BaseSource):
    """
    Polls KuCoin /api/v1/market/allTickers every `poll_interval` seconds.
    
    KuCoin API details:
    
    - Method: GET
    - Response format::
    
        {
          "code": "200000",
          "data": {
            "time": 1713264000000,
            "ticker": [
              {
                "symbol":     "BTC-USDT",
                "last":       "84500.12",
                "vol":        "1234.5678",
                "volValue":   "104265000",
                "buy":        "84499.00",
                "sell":       "84501.00"
              }
            ]
          }
        }

    Note: KuCoin returns USD prices. No conversion needed.
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        pairs: Optional[Dict[str, str]] = None,
        poll_interval: float = 5.0,
    ):
        if symbols is None:
            symbols = list(_DEFAULT_PAIRS.keys())

        self._kucoin_map: Dict[str, str] = {}
        for s in symbols:
            if pairs and s in pairs:
                self._kucoin_map[s] = pairs[s]
            elif s in _DEFAULT_PAIRS:
                self._kucoin_map[s] = _DEFAULT_PAIRS[s]
            else:
                logger.warning(f"[kucoin] no pair mapping for {s}, skipping")

        # Reverse map: KuCoin symbol → internal symbol (for fast lookup)
        self._reverse_map: Dict[str, str] = {
            v: k for k, v in self._kucoin_map.items()
        }

        symbol_map = dict(self._kucoin_map)

        super().__init__(
            symbols=list(self._kucoin_map.keys()),
            symbol_map=symbol_map,
            poll_interval=poll_interval,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "kucoin"

    async def start(self) -> None:
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "VeriLogos/1.0"},
        )
        await super().start()

    async def stop(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        await super().stop()

    async def fetch_ticks(self) -> List[MarketTick]:
        if not self._session:
            logger.error(f"[{self.name}] session not initialized")
            return []

        ticks: List[MarketTick] = []
        now = time.time()

        try:
            async with self._session.get(_TICKERS_URL) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"[{self.name}] HTTP {resp.status}: {body[:200]}")
                    return []

                data = await resp.json()

                if data.get("code") != "200000":
                    logger.warning(
                        f"[{self.name}] API code: {data.get('code')} "
                        f"msg: {data.get('msg', '')}"
                    )
                    return []

                ticker_list = data.get("data", {}).get("ticker", [])

                if not ticker_list:
                    logger.warning(f"[{self.name}] empty ticker list")
                    return []

                for item in ticker_list:
                    kc_symbol = item.get("symbol", "")
                    internal_sym = self._reverse_map.get(kc_symbol)

                    if internal_sym is None:
                        continue  # not in our watch list

                    price_str = item.get("last")
                    vol_str = item.get("vol", "0")

                    if not price_str:
                        continue

                    try:
                        price = float(price_str)
                        volume = float(vol_str)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"[{self.name}] bad price/vol for {kc_symbol}: "
                            f"price={price_str!r}, vol={vol_str!r}"
                        )
                        continue

                    tick = MarketTick(
                        symbol=internal_sym,
                        price=price,
                        volume=volume,
                        timestamp=now,
                    )
                    ticks.append(tick)
                    self._last_prices[internal_sym] = price

        except aiohttp.ClientError as e:
            logger.error(f"[{self.name}] request failed: {e}")
        except Exception as e:
            logger.error(f"[{self.name}] unexpected error: {e}", exc_info=True)

        logger.debug(f"[{self.name}] fetched {len(ticks)} ticks")
        return ticks
