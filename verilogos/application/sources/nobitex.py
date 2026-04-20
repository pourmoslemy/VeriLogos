# verilogos/application/sources/nobitex.py
"""Nobitex exchange data source (REST polling, API v2)."""

from typing import List, Dict, Optional
import logging
import time

import aiohttp

from verilogos.application.models import MarketTick
from verilogos.application.sources.base import BaseSource

logger = logging.getLogger(__name__)

# Nobitex v2 stats endpoint — requires POST
_STATS_URL = "https://apiv2.nobitex.ir/market/stats"

# Default symbol mapping: internal → (srcCurrency, dstCurrency)
_DEFAULT_PAIRS: Dict[str, tuple] = {
    "BTCIRT":   ("btc",   "rls"),
    "ETHIRT":   ("eth",   "rls"),
    "USDTIRT":  ("usdt",  "rls"),
    "XRPIRT":   ("xrp",   "rls"),
    "ADAIRT":   ("ada",   "rls"),
    "DOTIRT":   ("dot",   "rls"),
    "SOLIRT":   ("sol",   "rls"),
    "AVAXIRT":  ("avax",  "rls"),
    "MATICIRT": ("matic", "rls"),
    "LINKIRT":  ("link",  "rls"),
}


class NobitexSource(BaseSource):
    """
    Polls Nobitex /market/stats every `poll_interval` seconds.
    
    Nobitex v2 API details:
    
    - Method: POST
    - Body: {"srcCurrency": "btc,eth,usdt", "dstCurrency": "rls"}
    - Response format::
    
        {
          "status": "ok",
          "stats": {
            "btc-rls": {
              "bestSell": "55000000000",
              "bestBuy":  "54900000000",
              "latest":   "54950000000",
              "dayClose":  "...",
              "volumeSrc": "12.345"
            }
          }
        }

    Note: Nobitex uses "rls" (Rials) not "irt" (Toman).
          1 IRT = 10 RLS. We convert to Toman in output.
    """

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        pairs: Optional[Dict[str, tuple]] = None,
        poll_interval: float = 5.0,
        convert_to_toman: bool = True,
    ):
        if symbols is None:
            symbols = list(_DEFAULT_PAIRS.keys())

        # Build pair info
        self._pairs: Dict[str, tuple] = {}
        for s in symbols:
            if pairs and s in pairs:
                self._pairs[s] = pairs[s]
            elif s in _DEFAULT_PAIRS:
                self._pairs[s] = _DEFAULT_PAIRS[s]
            else:
                logger.warning(f"[nobitex] no pair mapping for {s}, skipping")

        self._convert_to_toman = convert_to_toman

        # Build native symbol map for BaseSource (internal → "src-dst")
        symbol_map = {
            s: f"{src}-{dst}" for s, (src, dst) in self._pairs.items()
        }

        super().__init__(
            symbols=list(self._pairs.keys()),
            symbol_map=symbol_map,
            poll_interval=poll_interval,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "nobitex"

    async def start(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            headers={
                "User-Agent": "VeriLogos/1.0",
                "Content-Type": "application/json",
            },
        )
        await super().start()

    async def stop(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        await super().stop()

    async def fetch_ticks(self) -> List[MarketTick]:
        """Fetch latest price for all symbols from Nobitex stats API."""
        if not self._session:
            logger.error(f"[{self.name}] session not initialized — call start() first")
            return []

        ticks: List[MarketTick] = []
        now = time.time()

        # Build request body
        src_currencies = set()
        dst_currencies = set()
        for src, dst in self._pairs.values():
            src_currencies.add(src)
            dst_currencies.add(dst)

        payload = {
            "srcCurrency": ",".join(sorted(src_currencies)),
            "dstCurrency": ",".join(sorted(dst_currencies)),
        }

        try:
            async with self._session.post(_STATS_URL, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        f"[{self.name}] HTTP {resp.status}: {body[:200]}"
                    )
                    return []

                data = await resp.json()

                if data.get("status") != "ok":
                    logger.warning(f"[{self.name}] API status: {data.get('status')}")
                    return []

                stats = data.get("stats", {})

                if not stats:
                    logger.warning(f"[{self.name}] empty stats in response")
                    logger.debug(f"[{self.name}] response keys: {list(data.keys())}")
                    return []

                for internal_sym, native_key in self._to_native.items():
                    pair_data = stats.get(native_key)
                    if pair_data is None:
                        logger.debug(
                            f"[{self.name}] no data for {native_key} "
                            f"(available: {list(stats.keys())[:5]}...)"
                        )
                        continue

                    price_str = pair_data.get("latest") or pair_data.get("dayClose")
                    vol_str = pair_data.get("volumeSrc", "0")

                    if not price_str:
                        continue

                    try:
                        price = float(price_str)
                        volume = float(vol_str)
                    except (ValueError, TypeError):
                        logger.warning(
                            f"[{self.name}] bad price/vol for {native_key}: "
                            f"price={price_str!r}, vol={vol_str!r}"
                        )
                        continue

                    # Nobitex returns Rials, convert to Toman
                    if self._convert_to_toman:
                        price = price / 10.0

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
