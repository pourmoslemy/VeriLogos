import csv
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

SYMBOLS = {
    "btc_usdt": {"base_price": 65000.0, "volatility": 450.0},
    "eth_usdt": {"base_price": 3200.0, "volatility": 45.0},
    "bnb_usdt": {"base_price": 600.0, "volatility": 8.0},
    "sol_usdt": {"base_price": 170.0, "volatility": 4.5},
    "ada_usdt": {"base_price": 0.65, "volatility": 0.02},
    "xrp_usdt": {"base_price": 0.75, "volatility": 0.02},
    "dot_usdt": {"base_price": 8.5, "volatility": 0.25},
    "avax_usdt": {"base_price": 40.0, "volatility": 1.5},
    "link_usdt": {"base_price": 16.0, "volatility": 0.5},
    "doge_usdt": {"base_price": 0.15, "volatility": 0.004},
}


def generate_ohlcv_rows(base_price: float, volatility: float, start_dt: datetime, bars: int):
    rows = []
    current_price = base_price

    for index in range(bars):
        current_dt = start_dt + timedelta(hours=index)
        timestamp = float(current_dt.timestamp())

        step = np.random.normal(0.0, volatility)
        close_price = max(current_price + step, base_price * 0.25)
        open_price = current_price

        wick_up = abs(np.random.normal(0.0, volatility * 0.20))
        wick_down = abs(np.random.normal(0.0, volatility * 0.20))
        high_price = max(open_price, close_price) + wick_up
        low_price = max(min(open_price, close_price) - wick_down, 0.0)
        volume = np.random.uniform(1000.0, 9000.0)

        rows.append(
            {
                "timestamp": timestamp,
                "open": round(open_price, 8),
                "high": round(high_price, 8),
                "low": round(low_price, 8),
                "close": round(close_price, 8),
                "volume": round(volume, 2),
            }
        )
        current_price = close_price

    return rows


def main():
    np.random.seed(42)
    output_dir = Path("historical_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=120)
    total_bars = 120 * 24

    generated = []
    for symbol, cfg in SYMBOLS.items():
        rows = generate_ohlcv_rows(
            base_price=cfg["base_price"],
            volatility=cfg["volatility"],
            start_dt=start_dt,
            bars=total_bars,
        )
        csv_path = output_dir / f"{symbol}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(
                file_obj,
                fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
            )
            writer.writeheader()
            writer.writerows(rows)
        generated.append((symbol, csv_path, rows))

    print("Generated CSV files:")
    for symbol, csv_path, rows in generated:
        closes = [row["close"] for row in rows]
        print(
            f"- {symbol}: {csv_path} | bars={len(rows)} | "
            f"close_range=({min(closes):.6f}, {max(closes):.6f})"
        )

    print(f"Total files generated: {len(generated)}")
    print(f"Output directory: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
