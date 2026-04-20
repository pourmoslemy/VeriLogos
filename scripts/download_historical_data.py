#!/usr/bin/env python3
"""Download historical 1h OHLCV data for VeriLogos backtests."""

import asyncio
import csv
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

SYMBOLS: Dict[str, str] = {
    "BTC/USDT": "BTC",
    "ETH/USDT": "ETH",
    "BNB/USDT": "BNB",
    "SOL/USDT": "SOL",
    "XRP/USDT": "XRP",
    "ADA/USDT": "ADA",
    "AVAX/USDT": "AVAX",
    "DOT/USDT": "DOT",
    "LINK/USDT": "LINK",
    "DOGE/USDT": "DOGE",
}

# Use the exact timestamps requested.
START_TS = 1735689600
END_TS = 1744675200
INTERVAL_SEC = 3600
MAX_REQUESTS_PER_SEC = 5.0
RETRY_BACKOFFS = [1, 2, 4]
MIN_VALID_ROWS = 10000
DATA_DIR = Path("historical_data")


@dataclass
class Candle:
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float


class RateLimiter:
    """Simple async global rate limiter (max requests per second)."""

    def __init__(self, rate_per_sec: float):
        self.min_interval = 1.0 / rate_per_sec
        self._next_allowed = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval


async def fetch_json(
    session: aiohttp.ClientSession,
    limiter: RateLimiter,
    url: str,
    params: Dict[str, str],
) -> Optional[dict]:
    """Fetch JSON with retries and exponential backoff."""
    attempt = 0
    max_attempts = len(RETRY_BACKOFFS) + 1
    while attempt < max_attempts:
        await limiter.wait()
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                text = await resp.text()
                raise RuntimeError(f"HTTP {resp.status}: {text[:200]}")
        except Exception as exc:
            if attempt >= len(RETRY_BACKOFFS):
                print(f"  request failed after retries: {exc}")
                return None
            backoff = RETRY_BACKOFFS[attempt]
            await asyncio.sleep(backoff)
            attempt += 1
    return None


def safe_name(symbol: str) -> str:
    return symbol.replace("/", "_").lower()


def ts_to_utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_existing_info(path: Path) -> Tuple[int, Optional[float], Optional[float]]:
    if not path.exists():
        return 0, None, None
    count = 0
    first_ts = None
    last_ts = None
    with open(path, "r", newline="", encoding="utf-8") as file_obj:
        reader = csv.DictReader(file_obj)
        for row in reader:
            count += 1
            try:
                ts = float(row.get("timestamp", 0))
            except (TypeError, ValueError):
                continue
            if first_ts is None:
                first_ts = ts
            last_ts = ts
    return count, first_ts, last_ts


def write_csv(path: Path, candles: List[Candle]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for candle in candles:
            writer.writerow(
                [
                    f"{candle.timestamp:.1f}",
                    candle.open,
                    candle.high,
                    candle.low,
                    candle.close,
                    candle.volume,
                ]
            )


def validate_candles(symbol: str, candles: List[Candle]) -> None:
    if not candles:
        raise ValueError(f"{symbol}: no candles downloaded")

    first_ts = candles[0].timestamp
    if abs(first_ts - START_TS) > INTERVAL_SEC * 2:
        raise ValueError(
            f"{symbol}: first timestamp {first_ts} too far from start {START_TS}"
        )

    for idx in range(1, len(candles)):
        if candles[idx].timestamp < candles[idx - 1].timestamp:
            raise ValueError(f"{symbol}: timestamps are not sorted ascending")


async def detect_provider(session: aiohttp.ClientSession, limiter: RateLimiter) -> str:
    print("Detecting reachable API provider...")
    # A: CryptoCompare
    a_data = await fetch_json(
        session,
        limiter,
        "https://min-api.cryptocompare.com/data/v2/histohour",
        {"fsym": "BTC", "tsym": "USDT", "limit": "2", "toTs": str(END_TS)},
    )
    if isinstance(a_data, dict):
        nested = a_data.get("Data", {}).get("Data", [])
        if isinstance(nested, list) and nested:
            print("  Using provider: CryptoCompare")
            return "cryptocompare"

    # B: KuCoin
    b_data = await fetch_json(
        session,
        limiter,
        "https://api.kucoin.com/api/v1/market/candles",
        {
            "type": "1hour",
            "symbol": "BTC-USDT",
            "startAt": str(START_TS),
            "endAt": str(min(END_TS, START_TS + 12 * INTERVAL_SEC)),
        },
    )
    if isinstance(b_data, dict) and isinstance(b_data.get("data"), list):
        print("  Using provider: KuCoin")
        return "kucoin"

    # C: OKX
    c_data = await fetch_json(
        session,
        limiter,
        "https://www.okx.com/api/v5/market/candles",
        {"instId": "BTC-USDT", "bar": "1H", "limit": "5"},
    )
    if isinstance(c_data, dict) and isinstance(c_data.get("data"), list):
        print("  Using provider: OKX")
        return "okx"

    raise RuntimeError("No reachable provider found (A/B/C all failed)")


async def download_cryptocompare(
    session: aiohttp.ClientSession,
    limiter: RateLimiter,
    base_symbol: str,
) -> List[Candle]:
    url = "https://min-api.cryptocompare.com/data/v2/histohour"
    by_ts: Dict[int, Candle] = {}
    cursor = END_TS
    seen_cursor = set()

    while True:
        if cursor in seen_cursor:
            break
        seen_cursor.add(cursor)

        payload = await fetch_json(
            session,
            limiter,
            url,
            {
                "fsym": base_symbol,
                "tsym": "USDT",
                "limit": "2000",
                "toTs": str(cursor),
            },
        )
        rows = payload.get("Data", {}).get("Data", []) if isinstance(payload, dict) else []
        if not rows:
            break

        oldest = None
        for item in rows:
            ts = int(item.get("time", 0))
            if ts < START_TS or ts > END_TS:
                continue
            by_ts[ts] = Candle(
                timestamp=float(ts),
                open=float(item.get("open", 0)),
                high=float(item.get("high", 0)),
                low=float(item.get("low", 0)),
                close=float(item.get("close", 0)),
                volume=float(item.get("volumefrom", 0)),
            )
            if oldest is None or ts < oldest:
                oldest = ts

        if oldest is None:
            break
        if oldest <= START_TS:
            break
        cursor = oldest - INTERVAL_SEC

    return [by_ts[k] for k in sorted(by_ts.keys())]


async def download_kucoin(
    session: aiohttp.ClientSession,
    limiter: RateLimiter,
    base_symbol: str,
) -> List[Candle]:
    url = "https://api.kucoin.com/api/v1/market/candles"
    symbol = f"{base_symbol}-USDT"
    by_ts: Dict[int, Candle] = {}
    chunk_span = (1500 - 1) * INTERVAL_SEC
    cursor = START_TS

    while cursor <= END_TS:
        chunk_end = min(END_TS, cursor + chunk_span)
        payload = await fetch_json(
            session,
            limiter,
            url,
            {
                "type": "1hour",
                "symbol": symbol,
                "startAt": str(cursor),
                "endAt": str(chunk_end),
            },
        )
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        if not rows:
            cursor = chunk_end + INTERVAL_SEC
            continue

        for item in rows:
            # [time, open, close, high, low, volume, turnover]
            ts = int(float(item[0]))
            if ts < START_TS or ts > END_TS:
                continue
            by_ts[ts] = Candle(
                timestamp=float(ts),
                open=float(item[1]),
                high=float(item[3]),
                low=float(item[4]),
                close=float(item[2]),
                volume=float(item[5]),
            )

        cursor = chunk_end + INTERVAL_SEC

    return [by_ts[k] for k in sorted(by_ts.keys())]


async def download_okx(
    session: aiohttp.ClientSession,
    limiter: RateLimiter,
    base_symbol: str,
) -> List[Candle]:
    url = "https://www.okx.com/api/v5/market/candles"
    inst_id = f"{base_symbol}-USDT"
    by_ts: Dict[int, Candle] = {}
    cursor_ms = (END_TS + INTERVAL_SEC) * 1000
    seen_cursor = set()

    while True:
        if cursor_ms in seen_cursor:
            break
        seen_cursor.add(cursor_ms)

        payload = await fetch_json(
            session,
            limiter,
            url,
            {
                "instId": inst_id,
                "bar": "1H",
                "before": str(cursor_ms),
                "limit": "300",
            },
        )
        rows = payload.get("data", []) if isinstance(payload, dict) else []
        if not rows:
            break

        oldest_ts = None
        for item in rows:
            # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            ts = int(int(item[0]) / 1000)
            if ts < START_TS or ts > END_TS:
                continue
            by_ts[ts] = Candle(
                timestamp=float(ts),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
            if oldest_ts is None or ts < oldest_ts:
                oldest_ts = ts

        if oldest_ts is None:
            break
        if oldest_ts <= START_TS:
            break
        cursor_ms = (oldest_ts * 1000) - 1

    return [by_ts[k] for k in sorted(by_ts.keys())]


async def download_symbol(
    session: aiohttp.ClientSession,
    limiter: RateLimiter,
    provider: str,
    symbol: str,
    base_symbol: str,
) -> List[Candle]:
    if provider == "cryptocompare":
        return await download_cryptocompare(session, limiter, base_symbol)
    if provider == "kucoin":
        return await download_kucoin(session, limiter, base_symbol)
    if provider == "okx":
        return await download_okx(session, limiter, base_symbol)
    raise RuntimeError(f"Unknown provider: {provider}")


async def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=20, ssl=False)
    headers = {"User-Agent": "VeriLogos-Historical-Downloader/1.0"}
    limiter = RateLimiter(MAX_REQUESTS_PER_SEC)

    summary_rows: List[Tuple[str, int, Optional[float], Optional[float], str]] = []

    async with aiohttp.ClientSession(timeout=timeout, connector=connector, headers=headers) as session:
        provider = await detect_provider(session, limiter)
        print(f"Downloading range: {START_TS} ({ts_to_utc(START_TS)} UTC) -> {END_TS} ({ts_to_utc(END_TS)} UTC)\n")

        for symbol, base_symbol in SYMBOLS.items():
            filename = f"{safe_name(symbol)}.csv"
            out_path = DATA_DIR / filename

            existing_count, existing_first, existing_last = read_existing_info(out_path)
            if existing_count > MIN_VALID_ROWS:
                print(f"[{symbol}] skip existing file ({existing_count} rows): {filename}")
                summary_rows.append((filename, existing_count, existing_first, existing_last, "skipped"))
                continue

            print(f"[{symbol}] downloading via {provider} -> {filename}")
            candles = await download_symbol(session, limiter, provider, symbol, base_symbol)
            print(f"[{symbol}] downloaded {len(candles)} candles")

            if not candles:
                print(f"[{symbol}] ERROR: no candles returned")
                summary_rows.append((filename, 0, None, None, "failed"))
                continue

            try:
                validate_candles(symbol, candles)
            except Exception as exc:
                print(f"[{symbol}] ERROR: validation failed before save: {exc}")
                summary_rows.append((filename, len(candles), candles[0].timestamp, candles[-1].timestamp, "failed"))
                continue

            write_csv(out_path, candles)
            row_count, first_ts, last_ts = read_existing_info(out_path)

            try:
                if row_count > 0:
                    validate_candles(symbol, candles)
            except Exception as exc:
                print(f"[{symbol}] ERROR: validation failed after save: {exc}")
                summary_rows.append((filename, row_count, first_ts, last_ts, "failed"))
                continue

            summary_rows.append((filename, row_count, first_ts, last_ts, "ok"))

    print("\nFinal summary:")
    print("file,rows,first_utc,last_utc,status")
    for file_name, rows, first_ts, last_ts, status in summary_rows:
        first_str = ts_to_utc(first_ts) if first_ts is not None else "-"
        last_str = ts_to_utc(last_ts) if last_ts is not None else "-"
        print(f"{file_name},{rows},{first_str},{last_str},{status}")


if __name__ == "__main__":
    asyncio.run(main())
