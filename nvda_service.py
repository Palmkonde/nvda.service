"""
nvda_service.py — NVDA stock price monitor 
- Fetches price every 60s → logs to stdout + file
- At 4 PM Eastern → logs daily min/max + change vs prev close
- Handles SIGTERM gracefully
- Persists state to JSON so restarts don't lose history
"""

import json
import logging
import os
import signal
import sys
import threading
import yfinance as yf
from datetime import time as dt_time
from datetime import datetime, timezone, timedelta

# ── Config ─────────────────────────────────────────────────────────────────────
SYMBOL       = "NVDA"
INTERVAL     = 60                          # seconds between price fetches
EOD_HOUR     = 16                          # 4 PM
UTC_OFFSET   = -4                          # Eastern Daylight Time (use -5 in winter)
STATE_FILE   = "state.json"
LOG_FILE     = "nvda.log"

EASTERN = timezone(timedelta(hours=UTC_OFFSET))

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger(__name__)

# ── Shared state ───────────────────────────────────────────────────────────────
state_lock = threading.Lock()
state = {}   # keys: date, min, max, last, prev_close

def load_state():
    global state
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        state.pop("last_reported", None)
        log.info("Loaded state: %s", state)
    except FileNotFoundError:
        log.info("No state file found, starting fresh")

def save_state():
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

def update_state(price):
    today = datetime.now(EASTERN).date().isoformat()
    with state_lock:
        if state.get("date") != today:
            prev_close = state.get("last", price)
            state.update({"date": today, "min": price, "max": price,
                          "last": price, "prev_close": prev_close})
            log.info("New day — rolled over state (prev_close=%.2f)", prev_close)
        else:
            state["min"]  = min(state["min"], price)
            state["max"]  = max(state["max"], price)
            state["last"] = price
        save_state()

# ── Yahoo Finance ──────────────────────────────────────────────────────────────
def fetch_price():
    ticker = yf.Ticker(SYMBOL)
    return float(ticker.fast_info["lastPrice"])

def fetch_historical(date: str) -> dict:
    """
    Fetch OHLC for a specific past date (format: 'YYYY-MM-DD').
    Returns dict with open, high, low, close or raises on failure.
    """
    day = datetime.strptime(date, "%Y-%m-%d")
    next_day = day + timedelta(days=1)
    df = yf.download(
        SYMBOL,
        start=day.strftime("%Y-%m-%d"),
        end=next_day.strftime("%Y-%m-%d"),
        interval="1d",
        progress=False
    )

    if df.empty:
        raise ValueError(f"No data returned for {date}")

    row = df.iloc[0]
    ticker = yf.Ticker(SYMBOL)
    prev = ticker.fast_info["previousClose"]

    return {
        "date":       date,
        "min":        float(row["Low"].iloc[0]),
        "max":        float(row["High"].iloc[0]),
        "last":       float(row["Close"].iloc[0]),
        "prev_close": float(prev),
    }

# ── Ticker thread ──────────────────────────────────────────────────────────────
def is_market_open() -> bool:
    now = datetime.now(EASTERN)

    if now.weekday() > 4:
        return False
    
    market = yf.Market("US")
    return market.status.get('status') == "open"

def ticker_loop(stop):
    log.info("Ticker started (every %ds)", INTERVAL)
    while not stop.is_set():
        if is_market_open():
            try:
                price = fetch_price()
                update_state(price)
                log.info("NVDA $%.2f  (min=%.2f  max=%.2f)",
                        price, state["min"], state["max"])
            except Exception as e:
                log.warning("Fetch failed: %s", e)
        else:
            log.debug("Market closed, not fetch")
        stop.wait(INTERVAL)
    log.info("Ticker stopped")

# ── EOD thread ─────────────────────────────────────────────────────────────────
def last_market_close() -> datetime:
    """Return the most recent past 4 PM Eastern (today or previous weekday)."""
    market = yf.Market("US").status
    log.debug(market)

    close = market.get("close")
    status = market.get("yfit_market_status")

    # Market is open OR will open today — today's close hasn't happened yet
    if status in ("YFT_MARKET_OPEN", "YFT_MARKET_WILL_OPEN"):
        close -= timedelta(days=1)
        while close.weekday() >= 5:
            close -= timedelta(days=1)
        close = close.replace(hour=EOD_HOUR, minute=0, second=0, microsecond=0)

    return close.astimezone(EASTERN)


def eod_loop(stop):
    log.info("EOD started (fires at %02d:00 Eastern)", EOD_HOUR)

    while not stop.is_set():
        missed      = last_market_close()
        missed_date = missed.date().isoformat()

        # ── Read last_reported from state instead of local variable ──────────
        with state_lock:
            last_reported = state.get("last_reported")

        if missed_date != last_reported:
            if state.get("date") != missed_date:
                log.info("No state for %s, fetching historical data...", missed_date)
                try:
                    historical = fetch_historical(missed_date)
                    with state_lock:
                        state.update(historical)
                        save_state()
                except Exception as e:
                    log.warning("Historical fetch failed: %s", e)

            if state.get("date") == missed_date:
                with state_lock:
                    state["last_reported"] = missed_date  # ← persist it
                    save_state()

                log.info("Catch-up report for %s", missed_date)
                eod_report()

        # ── Wait for next 4 PM weekday ────────────────────────────────────────
        now    = datetime.now(EASTERN)
        target = now.replace(hour=EOD_HOUR, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        while target.weekday() >= 5:
            target += timedelta(days=1)

        wait = (target - now).total_seconds()
        log.info("EOD: next report in %.0f min (at %s) (Eastern Time)",
                 wait / 60, target.strftime("%a %Y-%m-%d %H:%M"))
        stop.wait(wait)

    log.info("EOD stopped")


def eod_report():
    """Extracted so both the catch-up path and the normal path can call it."""
    with state_lock:
        s = state.copy()

    if not s:
        log.warning("EOD report: no state available")
        return

    change = s["last"] - s["prev_close"]
    pct    = change / s["prev_close"] * 100 if s["prev_close"] else 0
    arrow  = "▲" if change >= 0 else "▼"
    log.info("─── EOD REPORT (%s) ───────────────────────────", s["date"])
    log.info("  Close:  $%.2f", s["last"])
    log.info("  Range:  $%.2f – $%.2f", s["min"], s["max"])
    log.info("  Change: %s $%.2f  (%+.2f%%)  vs prev $%.2f",
             arrow, abs(change), pct, s["prev_close"])
    log.info("───────────────────────────────────────────────")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("nvda-service starting")
    load_state()

    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: (log.info("SIGTERM received"), stop.set()))
    signal.signal(signal.SIGINT,  lambda *_: (log.info("SIGINT received"),  stop.set()))

    threads = [
        threading.Thread(target=ticker_loop, args=(stop,), name="ticker", daemon=True),
        threading.Thread(target=eod_loop,    args=(stop,), name="eod",    daemon=True),
    ]
    for t in threads:
        t.start()

    stop.wait()
    for t in threads:
        t.join(timeout=10)
    log.info("nvda-service stopped")

if __name__ == "__main__":
    main()
