import numpy as np
from sklearn.linear_model import LinearRegression
from database import get_conn
from fastapi import HTTPException
from data_processing import (
    fetch_and_store,
    
)

def create_dataset(prices, window_size=5):
    X, y = [], []
    for i in range(len(prices) - window_size):
        X.append(prices[i:i+window_size])
        y.append(prices[i+window_size])
    return np.array(X), np.array(y)


def train_model(prices, window_size=5):
    X, y = create_dataset(prices, window_size)

    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(X, y)

    return model


def predict_prices(symbol: str, days_ahead=5):
    """
    Predict next N days using sliding window ML model
    """
    ensure_data(symbol)

    conn = get_conn()
    rows = conn.execute("""
        SELECT close FROM stock_data
        WHERE symbol=?
        ORDER BY date
    """, (symbol,)).fetchall()
    conn.close()

    prices = np.array([r["close"] for r in rows])

    if len(prices) < 10:
        return []

    window_size = 5
    model = train_model(prices, window_size)

    last_window = prices[-window_size:]
    predictions = []

    for _ in range(days_ahead):
        pred = model.predict([last_window])[0]
        predictions.append(round(float(pred), 2))

        # slide window
        last_window = np.append(last_window[1:], pred)

    return predictions


def ensure_data(symbol: str):
    """Fetch data if the symbol has no rows in DB."""
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM stock_data WHERE symbol=?", (symbol,)
    ).fetchone()
    conn.close()
    if row["cnt"] == 0:
        ok = fetch_and_store(symbol)
        if not ok:
            raise HTTPException(404, f"No data found for {symbol}")