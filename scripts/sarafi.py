"""
Test connectivity to crypto exchanges — Windows-friendly, zero dependencies.
Run:  python test_apis.py
"""

import urllib.request
import json
import time
import ssl

# --- Skip SSL verification (some Iranian ISPs mess with certs) ---
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

APIS = {
    # ── Iranian Exchanges ──
    "Nobitex OHLCV": {
        "url": "https://apiv2.nobitex.ir/market/udf/history"
               "?symbol=BTCUSDT&resolution=60&from=1744700000&to=1744786400",
        "type": "udf",
    },
    "Nobitex Stats": {
        "url": "https://apiv2.nobitex.ir/market/stats",
        "type": "json",
    },
    "Wallex OHLCV": {
        "url": "https://api.wallex.ir/v1/udf/history"
               "?symbol=BTCUSDT&resolution=60&from=1744700000&to=1744786400",
        "type": "udf",
    },
    "Ramzinex Pairs": {
        "url": "https://publicapi.ramzinex.com/exchange/api/v1.0/exchange/pairs",
        "type": "json",
    },
    "Exir Chart": {
        "url": "https://api.exir.io/v2/chart"
               "?symbol=btc-usdt&resolution=60&from=1744700000&to=1744786400",
        "type": "udf",
    },

    # ── International Exchanges (filter/sanctions test) ──
    "Binance Klines": {
        "url": "https://api.binance.com/api/v3/klines"
               "?symbol=BTCUSDT&interval=1h"
               "&startTime=1744700000000&endTime=1744786400000&limit=3",
        "type": "array",
    },
    "CoinGecko Price": {
        "url": "https://api.coingecko.com/api/v3/simple/price"
               "?ids=bitcoin,ethereum&vs_currencies=usd",
        "type": "json",
    },
    "CryptoCompare": {
        "url": "https://min-api.cryptocompare.com/data/v2/histohour"
               "?fsym=BTC&tsym=USDT&limit=3&toTs=1744786400",
        "type": "json",
    },
    "KuCoin Klines": {
        "url": "https://api.kucoin.com/api/v1/market/candles"
               "?type=1hour&symbol=BTC-USDT&startAt=1744700000&endAt=1744786400",
        "type": "json",
    },
    "OKX Candles": {
        "url": "https://www.okx.com/api/v5/market/candles"
               "?instId=BTC-USDT&bar=1H&limit=3",
        "type": "json",
    },
}


def count_items(body, api_type):
    """Try to count how many data items we got."""
    try:
        if api_type == "udf" and isinstance(body, dict):
            return len(body.get("t", []))
        if api_type == "array" and isinstance(body, list):
            return len(body)
        if isinstance(body, dict):
            # nested data
            for key in ("data", "Data", "result", "stats"):
                val = body.get(key)
                if isinstance(val, (list, dict)):
                    return len(val)
            return len(body)
        return 0
    except Exception:
        return -1


def test_api(name, info):
    url = info["url"]
    api_type = info["type"]

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
        })

        t0 = time.time()
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        raw = resp.read()
        elapsed = time.time() - t0

        status = resp.status
        size = len(raw)
        body = json.loads(raw)
        items = count_items(body, api_type)

        # Show a small preview
        preview = json.dumps(body, ensure_ascii=False)[:120]

        print(f"  ✅ {name:20s} | HTTP {status} | {elapsed:.2f}s | {size:>7,} bytes | items: {items}")
        print(f"     preview: {preview}...")
        print()
        return True

    except urllib.error.HTTPError as e:
        print(f"  ❌ {name:20s} | HTTP {e.code} — {e.reason}")
        try:
            err_body = e.read().decode()[:150]
            print(f"     body: {err_body}")
        except Exception:
            pass
        print()
        return False

    except urllib.error.URLError as e:
        print(f"  ❌ {name:20s} | URL ERROR — {e.reason}")
        print()
        return False

    except Exception as e:
        print(f"  ❌ {name:20s} | EXCEPTION — {type(e).__name__}: {e}")
        print()
        return False


def main():
    print("=" * 75)
    print("  EXCHANGE API CONNECTIVITY TEST")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 75)

    print("\n── Iranian Exchanges ──\n")
    iranian = ["Nobitex OHLCV", "Nobitex Stats", "Wallex OHLCV",
                "Ramzinex Pairs", "Exir Chart"]
    ok_count = 0
    for name in iranian:
        if test_api(name, APIS[name]):
            ok_count += 1

    print("\n── International Exchanges (sanctions/filter test) ──\n")
    international = ["Binance Klines", "CoinGecko Price", "CryptoCompare",
                      "KuCoin Klines", "OKX Candles"]
    for name in international:
        if test_api(name, APIS[name]):
            ok_count += 1

    total = len(APIS)
    print("=" * 75)
    print(f"  RESULT: {ok_count}/{total} APIs responded successfully")
    print("=" * 75)

    # Recommendation
    print("\n  📋 Recommendation for VeriLogos data source:")
    print("  Priority should be given to APIs that returned ✅ with OHLCV data.")
    print("  Look for entries with items > 0 (especially OHLCV/UDF types).\n")


if __name__ == "__main__":
    main()
