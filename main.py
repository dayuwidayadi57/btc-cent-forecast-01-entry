"""BTC cent forecast: 15% pull toward the 24h median close.

Reads every *.in JSON file in $MAKEFUN_INPUT_DIR (default /input),
takes markets[0].prices, and writes <id>.out with one forecast per file
into $MAKEFUN_OUTPUT_DIR (default /output).

Forecast: last = last close; centre = median of the last 1,440 closes
(24h); pull = (centre - last) * 0.15, clipped to +/-0.015 * last;
answer = round5(last + pull), clamped to 0.00001..9,999,999.99999.

Standard library only. No network, no randomness, no wall-clock.
Deterministic output.
"""

import json
import math
import os
import statistics
import sys
from pathlib import Path

WINDOW = 1440  # closes in 24h


def clean_prices(raw):
    """Keep only real, finite numbers; drop bools and non-finite values."""
    prices = []
    for value in raw:
        if isinstance(value, bool):
            continue
        if isinstance(value, dict):
            value = value.get("close")
            if isinstance(value, bool):
                continue
        if isinstance(value, (int, float)) and math.isfinite(value):
            prices.append(float(value))
    return prices


def forecast(prices):
    """One-step forecast from a list of cleaned closes."""
    if not prices:
        raise ValueError("no usable prices")
    last = prices[-1]
    if last <= 0:
        raise ValueError("last price must be positive")
    window = prices[-WINDOW:]
    centre = statistics.median(window)
    pull = (centre - last) * 0.15
    cap = 0.015 * last
    if pull > cap:
        pull = cap
    elif pull < -cap:
        pull = -cap
    answer = last + pull
    if answer < 0.00001:
        answer = 0.00001
    elif answer > 9999999.99999:
        answer = 9999999.99999
    return round(answer, 5)


def main():
    input_dir = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(input_dir.glob("*.in"))
    if not inputs:
        print("no *.in files found in %s" % input_dir, file=sys.stderr)
        return 1
    for in_path in inputs:
        case_id = in_path.stem
        with open(in_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        markets = data.get("markets")
        if not markets:
            raise ValueError("%s: missing markets" % case_id)
        prices = clean_prices(markets[0].get("prices", []))
        price = forecast(prices)
        payload = {"forecasts": [{"case": case_id, "price": price}]}
        out_path = output_dir / ("%s.out" % case_id)
        with open(out_path, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
