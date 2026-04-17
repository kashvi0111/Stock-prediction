from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
import numpy as np

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse


# IMPORT FROM  FILES
from data_processing import (
    fetch_live_price,
    fetch_and_store,
    ensure_data,
    COMPANIES
)


from model import predict_prices

from database import (
    get_conn,
    init_db
)

# ── App lifespan ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # preload some stocks
    for sym in ["TCS", "INFY", "RELIANCE", "HDFCBANK"]:
        try:
            fetch_and_store(sym)
        except:
            pass

    yield


app = FastAPI(
    title="Stock Data Intelligence index",
    version="1.0.0",
    lifespan=lifespan
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── APIs ────────────────────────────────────────────────




@app.get("/companies")
def get_companies():
    return [
        {"symbol": sym, **meta}
        for sym, meta in COMPANIES.items()
    ]


@app.get("/data/{symbol}")
def get_data(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    ensure_data(symbol)

    conn = get_conn()
    rows = conn.execute("""
        SELECT date, open, high, low, close, volume, daily_return, ma7
        FROM stock_data
        WHERE symbol=?
        ORDER BY date DESC LIMIT 30
    """, (symbol,)).fetchall()
    conn.close()

    return {
        "symbol": symbol,
        "company": COMPANIES[symbol]["name"],
        "data": [dict(r) for r in reversed(rows)],
    }


@app.get("/summary/{symbol}")
def get_summary(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    ensure_data(symbol)

    conn = get_conn()
    rows = conn.execute("""
        SELECT close, daily_return
        FROM stock_data
        WHERE symbol=?
        ORDER BY date DESC LIMIT 252
    """, (symbol,)).fetchall()
    conn.close()

    closes = [r["close"] for r in rows]
    returns = [r["daily_return"] for r in rows]

    volatility = round(float(np.std(returns)) * (252 ** 0.5) * 100, 2)

    return {
        "symbol": symbol,
        "company": COMPANIES[symbol]["name"],
        "week52_high": max(closes),
        "week52_low": min(closes),
        "avg_close": round(sum(closes) / len(closes), 2),
        "latest_close": closes[0],
        "volatility_pct": volatility,
    }


@app.get("/live/{symbol}")
def live_price(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    return fetch_live_price(symbol)


@app.get("/predict/{symbol}")
def predict(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    ensure_data(symbol)
    preds = predict_prices(symbol)

    return {
        "symbol": symbol,
        "company": COMPANIES[symbol]["name"],
        "prediction": preds
    }

@app.get("/gainers-losers")
def gainers_losers():
    results = []

    for sym in COMPANIES:
        conn = get_conn()
        row = conn.execute("""
            SELECT date, close, daily_return
            FROM stock_data
            WHERE symbol=?
            ORDER BY date DESC LIMIT 1
        """, (sym,)).fetchone()
        conn.close()

        if row:
            results.append({
                "symbol": sym,
                "name": COMPANIES[sym]["name"],
                "date": row["date"],
                "close": row["close"],
                "daily_return_pct": round(row["daily_return"] * 100, 2),
            })

    results.sort(key=lambda x: x["daily_return_pct"], reverse=True)

    return {
        "all": results,
        "top_gainers": results[:3],
        "top_losers": results[-3:][::-1],
    }



@app.get("/smart/{symbol}")
def smart(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    ensure_data(symbol)

    live = fetch_live_price(symbol)
    preds = predict_prices(symbol)

    conn = get_conn()
    last = conn.execute("""
        SELECT close FROM stock_data
        WHERE symbol=?
        ORDER BY date DESC LIMIT 1
    """, (symbol,)).fetchone()
    conn.close()

    signal = "HOLD 🟡"
    trend = "SIDEWAYS ➖"
    confidence = "Low"
    action_time = "Wait"
    description = "No clear trend. Better to wait."

    if preds and last:
        current_price = last["close"]
        predicted_price = preds[-1]

        change_pct = (predicted_price - current_price) / current_price * 100

        if change_pct > 2:
            signal = "STRONG BUY 🟢"
            trend = "UP 📈"
            confidence = "High"
            action_time = "Buy within 1 day"
            description = "Strong upward trend expected. Price may rise significantly. Buy immediately."

        elif change_pct > 0.5:
            signal = "BUY 🟢"
            trend = "UP 📈"
            confidence = "Medium"
            action_time = "Buy in 1-3 days"
            description = "Stock likely to rise moderately. Good time to buy soon."

        elif change_pct < -2:
            signal = "STRONG SELL 🔴"
            trend = "DOWN 📉"
            confidence = "High"
            action_time = "Sell immediately"
            description = "Strong drop expected. Price may fall sharply. Sell immediately."

        elif change_pct < -0.5:
            signal = "SELL 🔴"
            trend = "DOWN 📉"
            confidence = "Medium"
            action_time = "Sell in 1-2 days"
            description = "Stock may decline slightly. Consider selling soon."

        else:
            signal = "HOLD 🟡"
            trend = "SIDEWAYS ➖"
            confidence = "Low"
            action_time = "Wait"
            description = "No strong trend. Hold and wait for better opportunity."

    return {
        "symbol": symbol,
        "company": COMPANIES[symbol]["name"],
        "live_price": live,
        "predictions": preds,
        "trend": trend,
        "signal": signal,
        "confidence": confidence,
        "action_time": action_time,
        "description": description
    }



@app.get("/compare")
def compare_stocks(symbol1: str, symbol2: str):
    s1, s2 = symbol1.upper(), symbol2.upper()

    for s in [s1, s2]:
        if s not in COMPANIES:
            raise HTTPException(400, f"Invalid symbol {s}")
        ensure_data(s)

    conn = get_conn()

    def get_data(sym):
        rows = conn.execute("""
            SELECT date, close, daily_return
            FROM stock_data
            WHERE symbol=?
            ORDER BY date DESC LIMIT 30
        """, (sym,)).fetchall()
        return [dict(r) for r in reversed(rows)]

    d1 = get_data(s1)
    d2 = get_data(s2)
    conn.close()

    # Align dates
    dates1 = {r["date"]: r for r in d1}
    dates2 = {r["date"]: r for r in d2}
    common = sorted(set(dates1) & set(dates2))

    if not common:
        return {
            "dates": [],
            "normalised_prices": {s1: [], s2: []},
            "correlation": 0
        }

    c1 = [dates1[d]["close"] for d in common]
    c2 = [dates2[d]["close"] for d in common]

    base1, base2 = c1[0], c2[0]

    norm1 = [round(v / base1 * 100, 2) for v in c1]
    norm2 = [round(v / base2 * 100, 2) for v in c2]

    correlation = float(np.corrcoef(c1, c2)[0, 1])

    return {
        "dates": common,
        "normalised_prices": {
            s1: norm1,
            s2: norm2
        },
        "correlation": round(correlation, 4),
        "total_return_pct": {
            s1: round((c1[-1] - c1[0]) / c1[0] * 100, 2),
            s2: round((c2[-1] - c2[0]) / c2[0] * 100, 2),
        }
    }


@app.post("/refresh/{symbol}")
def refresh(symbol: str):
    symbol = symbol.upper()

    if symbol not in COMPANIES:
        raise HTTPException(400, "Invalid symbol")

    ok = fetch_and_store(symbol)
    return {"symbol": symbol, "refreshed": ok}


# ── index ───────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/dashboard.html")
def dashboard():
    return FileResponse("dashboard.html")


        
