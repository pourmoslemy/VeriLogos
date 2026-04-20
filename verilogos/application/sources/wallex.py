# verilogos/application/sources/wallex.py
"""Wallex exchange data source (REST polling, public API)."""

from typing import List, Dict, Optional
import logging
import time

import aiohttp

from verilogos.application.models import MarketTick
from verilogos.application.sources.base import BaseSource

logger = logging.getLogger(__name__)

# Wallex public API — no auth needed
_STATS_URL = "https://api.wallex.ir/v1/markets"

# Default symbol mapping: internal → Wallex symbol
_DEFAULT_PAIRS: Dict[str, str] = {
    "BTCIRT":   "BTCTMN",
    "ETHIRT":   "ETHTMN",
    "USDTIRT":  "USDTTMN",
    "XRPIRT":   "XRPTMN",
    "ADAIRT":   "ADATMN",
    "DOTIRT":   "DOTTMN",
    "SOLIRT":   "SOLTMN",
    "AVAXIRT":  "AVAXTMN",
    "MATICIRT": "MATICTMN",
    "LINKIRT":  "LINKTMN",
}


class WallexSource(BaseSource):
    """
    Polls Wallex /v1/markets every `poll_interval` seconds.

    Wallex API:
      - Method: GET
      - Response:
        {
          "result": {
            "symbols": {
              "BTCTMN": {
                "stats": {
                  "bidPrice":  "11440000000",
                  "askPrice":  "11445000000",
                  "24h_ch":    "-0.5",
                  "24h_volume": "12.34",
                  "lastPrice": "11442000000",
                  ...
                }
              },
              ...
            }
          },
          "success": true
        }

    Note: Wallex returns prices in Toman directly.
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        pairs: Optional[Dict[str, str]] = None,
        poll_interval: float = 5.0,
    ):
        if symbols is None:
            symbols = list(_DEFAULT_PAIRS.keys())

        # Build pair info
        self._wallex_map: Dict[str, str] = {}
        for s in symbols:
            if pairs and s in pairs:
                self._wallex_map[s] = pairs[s]
            elif s in _DEFAULT_PAIRS:
                self._wallex_map[s] = _DEFAULT_PAIRS[s]
            else:
                logger.warning(f"[wallex] no pair mapping for {s}, skipping")

        symbol_map = dict(self._wallex_map)

        super().__init__(
            symbols=list(self._wallex_map.keys()),
            symbol_map=symbol_map,
            poll_interval=poll_interval,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "wallex"

    async def start(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "VeriLogos/1.0"},
        )
        await super().start()

    async def stop(self):
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
            async with self._session.get(_STATS_URL) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"[{self.name}] HTTP {resp.status}: {body[:200]}")
                    return []

                data = await resp.json()

                if not data.get("success", False):
                    logger.warning(f"[{self.name}] API success=false")
                    return []

                symbols_data = (
                    data.get("result", {}).get("symbols", {})
                )

                if not symbols_data:
                    logger.warning(f"[{self.name}] empty symbols in response")
                    return []

                for internal_sym, wallex_sym in self._wallex_map.items():
                    pair_data = symbols_data.get(wallex_sym)
                    if pair_data is None:
                        logger.debug(
                            f"[{self.name}] no data for {wallex_sym}"
                        )
                        continue

                    stats = pair_data.get("stats", {})
                    price_str = stats.get("lastPrice")
                    vol_str = stats.get("24h_volume", "0")

                    if not price_str:
                        continue

                    try:
                        price = float(price_str)
                        volume = float(vol_str)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"[{self.name}] bad price/vol for {wallex_sym}: "
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
