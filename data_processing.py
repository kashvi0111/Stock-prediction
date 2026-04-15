import yfinance as yf
import pandas as pd
import numpy as np
from database import get_conn
from database import get_conn
from fastapi import HTTPException

COMPANIES = {
    "RELIANCE": {"name": "Reliance Industries", "sector": "Energy"},
    "TCS":      {"name": "Tata Consultancy Services", "sector": "IT"},
    "INFY":     {"name": "Infosys", "sector": "IT"},
    "HDFCBANK": {"name": "HDFC Bank", "sector": "Banking"},
    "ICICIBANK":{"name": "ICICI Bank", "sector": "Banking"},
    "WIPRO":    {"name": "Wipro", "sector": "IT"},
    "BAJFINANCE":{"name": "Bajaj Finance", "sector": "Finance"},
    "SBIN":     {"name": "State Bank of India", "sector": "Banking"},
    "HINDUNILVR":{"name": "Hindustan Unilever", "sector": "FMCG"},
    "KOTAKBANK":{"name": "Kotak Mahindra Bank", "sector": "Banking"},
}


def _generate_mock_data(symbol: str, days: int = 252) -> pd.DataFrame:
    """
    Generates realistic-looking mock OHLCV data using random walks.
    Used as a fallback when yfinance is unavailable (network restrictions, CI, etc.).
    """
    np.random.seed(abs(hash(symbol)) % 9999)   # reproducible per symbol
    base_prices = {
        "RELIANCE": 2800, "TCS": 3900, "INFY": 1500, "HDFCBANK": 1700,
        "ICICIBANK": 1100, "WIPRO": 480, "BAJFINANCE": 7200,
        "SBIN": 780, "HINDUNILVR": 2400, "KOTAKBANK": 1750,
    }
    start_price = base_prices.get(symbol, 1000)

    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    closes = [start_price]
    for _ in range(days - 1):
        closes.append(round(closes[-1] * (1 + np.random.normal(0.0003, 0.015)), 2))

    df = pd.DataFrame({
        "date":   dates.strftime("%Y-%m-%d"),
        "open":   [round(c * np.random.uniform(0.995, 1.005), 2) for c in closes],
        "high":   [round(c * np.random.uniform(1.002, 1.018), 2) for c in closes],
        "low":    [round(c * np.random.uniform(0.982, 0.998), 2) for c in closes],
        "close":  closes,
        "volume": np.random.randint(500_000, 5_000_000, days),
        "symbol": symbol,
    })
    return df


def fetch_and_store(symbol: str, period: str = "1y"):
    """Download data from yfinance, compute metrics, store in SQLite.
    Falls back to mock data if yfinance is unavailable."""
    df = pd.DataFrame()
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        raw = ticker.history(period=period)
        if not raw.empty:
            raw = raw.reset_index()
            raw.columns = [c.lower() for c in raw.columns]
            raw["date"] = pd.to_datetime(raw["date"]).dt.strftime("%Y-%m-%d")
            raw["symbol"] = symbol
            df = raw[["symbol", "date", "open", "high", "low", "close", "volume"]].copy()
    except Exception:
        pass   # network blocked or API error → use mock

    if df.empty:
        df = _generate_mock_data(symbol)

    if df.empty:
        return False

    # ── Calculated metrics ────────────────────────────────────────────────────
    df["daily_return"] = (df["close"] - df["open"]) / df["open"]
    df["ma7"] = df["close"].rolling(7, min_periods=1).mean()

    conn = get_conn()
    for _, row in df.iterrows():
        conn.execute("""
            INSERT OR REPLACE INTO stock_data
            (symbol, date, open, high, low, close, volume, daily_return, ma7)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            row["symbol"], row["date"],
            round(float(row["open"]), 2),
            round(float(row["high"]), 2),
            round(float(row["low"]), 2),
            round(float(row["close"]), 2),
            int(row["volume"]),
            round(float(row["daily_return"]), 6),
            round(float(row["ma7"]), 2),
        ))
    conn.commit()
    conn.close()
    return True

def fetch_live_price(symbol: str):
    """
    Fetch near real-time price (1-minute interval)
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        data = ticker.history(period="1d", interval="1m")

        if not data.empty:
            latest = data.iloc[-1]
            return {
                "symbol": symbol,
                "price": round(float(latest["Close"]), 2),
                "time": str(latest.name)
            }
    except Exception:
        pass

    return {
        "symbol": symbol,
        "price": None,
        "time": None
    }


def ensure_data(symbol: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) as cnt FROM stock_data WHERE symbol=?",
        (symbol,)
    ).fetchone()
    conn.close()

    if row["cnt"] == 0:
        ok = fetch_and_store(symbol)
        if not ok:
            raise HTTPException(404, f"No data found for {symbol}")
