import json
import sys
import math
import re
import pandas as pd
import sqlite3
import datetime
from sklearn.linear_model import LinearRegression

DB_PATH = "trading_data.db"

# --- Database Functions ---

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            signal TEXT NOT NULL,
            price REAL NOT NULL,
            direction TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_trade(signal, price, direction):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO trades (signal, price, direction)
        VALUES (?, ?, ?)
    ''', (signal, price, direction))
    conn.commit()
    conn.close()

def get_first_and_last_price(hours=1):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    # First price in the period
    c.execute(
        "SELECT price FROM trades WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT 1",
        (since,)
    )
    first_row = c.fetchone()
    # Last price in the period
    c.execute(
        "SELECT price FROM trades WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT 1",
        (since,)
    )
    last_row = c.fetchone()
    conn.close()
    return {
        "first": first_row[0] if first_row else None,
        "last": last_row[0] if last_row else None
    }

# --- Trading Logic ---

def macd(prices, short_window=12, long_window=26):
    short_ema = prices['close'].ewm(span=short_window, adjust=False).mean()
    long_ema = prices['close'].ewm(span=long_window, adjust=False).mean()
    return short_ema - long_ema

def dmi_adx(prices, window=14):
    df = prices.copy()
    df['upMove'] = df['high'] - df['high'].shift(1)
    df['downMove'] = df['low'].shift(1) - df['low']
    df['plusDM'] = df.apply(lambda row: row['upMove'] if row['upMove'] > row['downMove'] and row['upMove'] > 0 else 0, axis=1)
    df['minusDM'] = df.apply(lambda row: row['downMove'] if row['downMove'] > row['upMove'] and row['downMove'] > 0 else 0, axis=1)
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    df['TR'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = df['TR'].rolling(window=window).mean()
    df['plusDI'] = 100 * (df['plusDM'].rolling(window=window).sum() / df['ATR'])
    df['minusDI'] = 100 * (df['minusDM'].rolling(window=window).sum() / df['ATR'])
    df['DX'] = 100 * (abs(df['plusDI'] - df['minusDI']) / (df['plusDI'] + df['minusDI']))
    df['ADX'] = df['DX'].rolling(window=window).mean()
    return df[['plusDI', 'minusDI', 'ADX']]

def validate_data(data):
    required_keys = ['close', 'high', 'low']

    def is_valid_number(val):
        try:
            if isinstance(val, str):
                if not re.match(r'^-?\d+(\.\d+)?(e[+-]?\d+)?$', val, re.IGNORECASE):
                    return False
            num = float(val)
            if math.isnan(num) or math.isinf(num):
                return False
            return 0 <= num <= 1e6
        except Exception:
            return False

    if isinstance(data, dict):
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Invalid data. '{key}' field not present.")
            if not is_valid_number(data[key]):
                raise ValueError(f"Invalid data. '{key}' value is not a valid number or out of bounds.")
        return True
    elif isinstance(data, list):
        for idx, row in enumerate(data):
            for key in required_keys:
                if key not in row:
                    raise ValueError(f"Invalid data at index {idx}. '{key}' field not present.")
                if not is_valid_number(row[key]):
                    raise ValueError(f"Invalid data at index {idx}. '{key}' value is not a valid number or out of bounds.")
        return True
    else:
        raise ValueError("Invalid data format.")

def preprocess_data(data):
    df = pd.DataFrame(data)
    df['macd'] = macd(df)
    dmi_df = dmi_adx(df)
    df = pd.concat([df, dmi_df], axis=1)
    df = df.fillna(0)
    return df

def train_model(df):
    X = df[['macd', 'plusDI', 'minusDI', 'ADX']]
    y = df['close']
    model = LinearRegression()
    model.fit(X, y)
    return model

def generate_signals(df):
    signals = []
    prev_plusDI = df['plusDI'].iloc[0]
    prev_minusDI = df['minusDI'].iloc[0]
    for i, row in df.iterrows():
        plusDI = row['plusDI']
        minusDI = row['minusDI']
        adx = row['ADX']
        signal = "none"
        if plusDI > minusDI and adx > 25:
            signal = "long"
        elif minusDI > plusDI and adx > 25:
            signal = "short"
        if (prev_plusDI < prev_minusDI and plusDI > minusDI) or (prev_plusDI > prev_minusDI and plusDI < minusDI):
            signal = "crossover"
        signals.append(signal)
        prev_plusDI = plusDI
        prev_minusDI = minusDI
    return signals

# --- Main Loop ---

if __name__ == '__main__':
    init_db()
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            data = json.loads(line)
            if validate_data(data):
                df = preprocess_data(data)
                model = train_model(df)
                predictions = model.predict(df[['macd', 'plusDI', 'minusDI', 'ADX']])
                signals = generate_signals(df)
                # Store each signal and price in the database
                for i, signal in enumerate(signals):
                    price = float(df['close'].iloc[i])
                    direction = signal
                    insert_trade(signal, price, direction)
                last_hour_prices = get_first_and_last_price(hours=1)
                last_24h_prices = get_first_and_last_price(hours=24)
                output_data = {
                    'predictions': predictions.tolist(),
                    'signals': signals,
                    'originalData': data,
                    'lastHourPrices': last_hour_prices,
                    'last24hPrices': last_24h_prices
                }
                print(json.dumps(output_data))
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)