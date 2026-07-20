from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf


# Edit this list to change the symbols being scanned.
SYMBOLS = [
    "AAPL",
    "MSFT",
    "NVDA",
    "TSLA",
    "SPY",
    "QQQ",
]

TIMEFRAME = "1d"
MARKET_TIMEZONE = ZoneInfo("America/New_York")

CURRENT_RESULTS_FILE = Path("current_scan.csv")
HISTORY_FILE = Path("scan_history.csv")


def classify_candle(
    current_high: float,
    current_low: float,
    previous_high: float,
    previous_low: float,
) -> str:
    """Classify one candle by comparing it with the previous candle."""

    if current_high <= previous_high and current_low >= previous_low:
        return "1"

    if current_high > previous_high and current_low >= previous_low:
        return "2 Up"

    if current_low < previous_low and current_high <= previous_high:
        return "2 Down"

    if current_high > previous_high and current_low < previous_low:
        return "3"

    raise ValueError("The candle could not be classified.")


def is_signal(candle_type: str) -> bool:
    """Only candle types 1 and 3 are signals."""

    return candle_type in {"1", "3"}


def download_completed_daily_bars(symbol: str) -> pd.DataFrame:
    """
    Download daily bars and return the last two completed candles.

    When run before 4:10 PM New York time, today's candle is removed
    because it may still be incomplete.
    """

    data = yf.download(
        tickers=symbol,
        period="1mo",
        interval=TIMEFRAME,
        auto_adjust=True,
        progress=False,
        threads=False,
        multi_level_index=False,
    )

    if data.empty:
        raise RuntimeError("No price data was returned.")

    data = data.dropna(subset=["High", "Low"]).copy()

    now_new_york = datetime.now(MARKET_TIMEZONE)
    latest_date = pd.Timestamp(data.index[-1]).date()

    # Protect manual runs made while today's daily candle is incomplete.
    if (
        latest_date == now_new_york.date()
        and now_new_york.time() < time(16, 10)
    ):
        data = data.iloc[:-1]

    if len(data) < 2:
        raise RuntimeError("Fewer than two completed candles are available.")

    return data.iloc[-2:]


def scan_symbol(symbol: str, scanned_at: str) -> dict:
    bars = download_completed_daily_bars(symbol)

    previous = bars.iloc[-2]
    current = bars.iloc[-1]

    previous_high = float(previous["High"])
    previous_low = float(previous["Low"])
    current_high = float(current["High"])
    current_low = float(current["Low"])

    candle_type = classify_candle(
        current_high=current_high,
        current_low=current_low,
        previous_high=previous_high,
        previous_low=previous_low,
    )

    return {
        "Symbol": symbol,
        "Timeframe": TIMEFRAME,
        "CandleDate": pd.Timestamp(bars.index[-1]).date().isoformat(),
        "PreviousHigh": round(previous_high, 4),
        "PreviousLow": round(previous_low, 4),
        "CurrentHigh": round(current_high, 4),
        "CurrentLow": round(current_low, 4),
        "Candle": candle_type,
        "Signal": is_signal(candle_type),
        "ScannedAtUTC": scanned_at,
    }


def save_results(results: list[dict]) -> None:
    current_results = pd.DataFrame(results)
    current_results = current_results.sort_values("Symbol")

    current_results.to_csv(CURRENT_RESULTS_FILE, index=False)

    if HISTORY_FILE.exists():
        old_history = pd.read_csv(HISTORY_FILE)
        history = pd.concat(
            [old_history, current_results],
            ignore_index=True,
        )
    else:
        history = current_results.copy()

    # Keep one result per symbol, timeframe, and completed candle.
    history = history.drop_duplicates(
        subset=["Symbol", "Timeframe", "CandleDate"],
        keep="last",
    )

    history = history.sort_values(
        ["CandleDate", "Symbol"],
        ascending=[True, True],
    )

    history.to_csv(HISTORY_FILE, index=False)


def main() -> None:
    scanned_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
    )

    results: list[dict] = []

    for symbol in SYMBOLS:
        try:
            result = scan_symbol(symbol, scanned_at)
            results.append(result)

            print(
                f"{symbol}: "
                f"Candle = {result['Candle']}, "
                f"Signal = {result['Signal']}"
            )

        except Exception as error:
            print(f"{symbol}: ERROR = {error}")

    if not results:
        raise RuntimeError("No symbols were scanned successfully.")

    save_results(results)


if __name__ == "__main__":
    main()
