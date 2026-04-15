# 📈 Stock Data Intelligence Dashboard

> **JarNox Internship Assignment** — Mini financial data platform for Indian large-cap stocks

---

## 🚀 Quick Start

```bash
# 1. Clone / unzip the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server (auto-downloads data on first launch)
uvicorn main:app --reload

# 4. Open in browser
http://localhost:8000          # Dashboard
http://localhost:8000/docs     # Swagger UI (interactive API docs)
```

> **Note:** On first launch the app pre-fetches 1 year of data for TCS, INFY, RELIANCE, and HDFCBANK from yfinance. Other companies are fetched on demand when clicked.

---

## 🗂️ Project Structure

```
stock_dashboard/
├── main.py           # FastAPI backend — all routes + DB logic
├── dashboard.html    # Single-page frontend (Chart.js)
├── requirements.txt  # Python dependencies
├── README.md         # This file
└── stocks.db         # SQLite DB (auto-created on first run)
```

---

## ⚙️ Tech Stack

| Layer       | Technology                          |
|-------------|-------------------------------------|
| Language    | Python 3.11+                        |
| Backend     | **FastAPI** + Uvicorn               |
| Data source | **yfinance** (NSE real data)        |
| Database    | **SQLite** (via built-in `sqlite3`) |
| Data wrangling | **Pandas** + **NumPy**           |
| Frontend    | HTML + Vanilla JS + **Chart.js**    |

---

## 🧩 Assignment Parts Completed

### Part 1 — Data Collection & Preparation ✅

- Fetches **1 year** of OHLCV data from yfinance for 10 Indian NSE companies
- Stored in SQLite with proper date formatting
- **Computed metrics:**
  - `daily_return` = (CLOSE − OPEN) / OPEN
  - `ma7` = 7-day rolling average of close price
  - 52-week high/low computed on-the-fly from 252 trading days
- **Custom metric ✨:** Annualised Volatility = `std(daily_returns) × √252 × 100`

### Part 2 — REST API Development ✅

| Endpoint                         | Method | Description                                |
|----------------------------------|--------|--------------------------------------------|
| `/companies`                     | GET    | List all 10 tracked companies              |
| `/data/{symbol}`                 | GET    | Last 30 days OHLCV + metrics               |
| `/summary/{symbol}`              | GET    | 52-week high, low, avg close, volatility   |
| `/compare?symbol1=X&symbol2=Y`   | GET    | Normalised price comparison + correlation  |
| `/gainers-losers`                | GET    | Top 3 gainers and losers (custom insight)  |
| `/refresh/{symbol}`              | POST   | Force-refresh a symbol from yfinance       |

- Full **Swagger UI** at `/docs` (FastAPI auto-generates)
- CORS enabled for frontend integration

### Part 3 — Visualization Dashboard ✅

The dashboard at `http://localhost:8000` features:

- **Sidebar** — clickable company list with live daily return badges
- **Stats row** — latest price, today's change %, 52-week high/low, avg close, volatility
- **Closing Price chart** — line chart with 30 / 60 / 90-day filters
- **Daily Return Distribution** — bar chart (green = positive, red = negative)
- **7-Day MA vs Close** — overlay line chart showing trend vs smoothed average
- **Compare Two Stocks** — normalised (base 100) price comparison with Pearson correlation
- **Top Gainers & Losers** — ranked cards from latest session

---

## 📊 Data & Logic Explained

### Companies tracked (NSE)

RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, WIPRO, BAJFINANCE, SBIN, HINDUNILVR, KOTAKBANK

### Custom Metric: Annualised Volatility

```
σ_annual = std(daily_returns) × √252 × 100
```

Higher values indicate a more volatile (risky) stock. Useful for quick risk assessment without needing options data.

### Comparison: Normalised Price

Both stocks are normalised to a base of 100 at the start of the comparison window. This removes price-level bias and shows relative performance clearly.

### Pearson Correlation

Measures how similarly two stocks move day-to-day. Values near +1 mean they move together; near −1 means they move opposite; near 0 means they are largely independent.

---

## 🗃️ Database Schema

```sql
CREATE TABLE stock_data (
    symbol       TEXT,
    date         TEXT,        -- YYYY-MM-DD
    open         REAL,
    high         REAL,
    low          REAL,
    close        REAL,
    volume       INTEGER,
    daily_return REAL,        -- (close - open) / open
    ma7          REAL,        -- 7-day rolling avg close
    PRIMARY KEY (symbol, date)
);
```

---

## 📌 Design Decisions

1. **SQLite over PostgreSQL** — Zero-config, single-file DB. Easy to run locally without any server setup. Can be swapped to PostgreSQL by changing the connection string.

2. **yfinance over bhavcopy CSV** — Live data via yfinance provides a clean, authenticated source. No manual CSV download needed.

3. **On-demand fetching** — Data is fetched from yfinance only when a company is first accessed, keeping startup time fast.

4. **Single HTML file dashboard** — No build step required. The dashboard is served directly by FastAPI and uses Chart.js from CDN.

---

## 🔮 Optional Add-ons (What could be added next)

- 🧠 **Price prediction** using a simple linear regression or ARIMA model
- 🐳 **Docker** — `docker build -t stock-dash . && docker run -p 8000:8000 stock-dash`
- ☁️ **Deployment** on Render.com (add `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`)
- ⚡ **Redis caching** to avoid redundant yfinance calls
- 📰 **News sentiment** — fetch news headlines and score them for mock sentiment index

---

## 📬 Submission

Built with ❤️ for the JarNox Software Internship.  
Questions: [support@jarnox.com](mailto:support@jarnox.com)
