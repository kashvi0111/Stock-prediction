import sqlite3

DB_PATH = "stocks.db"

# ── Indian large-cap companies (NSE symbols + .NS suffix for yfinance) ──────


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            symbol      TEXT,
            date        TEXT,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      INTEGER,
            daily_return REAL,
            ma7         REAL,
            PRIMARY KEY (symbol, date)
        )
    """)
    conn.commit()
    conn.close()