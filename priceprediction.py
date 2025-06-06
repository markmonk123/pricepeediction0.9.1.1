import json
import sys
import math
import re
import pandas as pd
import sqlite3
import datetime
from sklearn.linear_model import LinearRegression
import numpy as np
from sklearn.preprocessing import MinMaxScaler

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
    try:
        price = round(float(price), 2)
    except (ValueError, TypeError):
        raise ValueError(f"Price value '{price}' cannot be cast to float for insert_trade.")
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
    def safe_round(val):
        try:
            return round(float(val), 2)
        except Exception:
            return None
    return {
        "first": safe_round(first_row[0]) if first_row else None,
        "last": safe_round(last_row[0]) if last_row else None
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
    if isinstance(data, dict):
        data = [data]
    df = pd.DataFrame(data)
    # Explicitly cast and round price columns
    for col in ['close', 'high', 'low']:
        try:
            df[col] = pd.to_numeric(df[col], errors='raise').round(2)
        except Exception as e:
            raise ValueError(f"Column '{col}' contains non-numeric values: {e}")
    df['macd'] = macd(df)
    dmi_df = dmi_adx(df)
    df = pd.concat([df, dmi_df], axis=1)
    df = df.fillna(0)
    # Also round the calculated columns
    for col in ['macd', 'plusDI', 'minusDI', 'ADX']:
        if col in df:
            df[col] = df[col].round(2)
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

EPOCH_WINDOWS = [8, 13, 20, 25, 50]

def normalize_df(df, window=15):
    """Normalize features using min-max scaling based on the last `window` rows."""
    scaler = MinMaxScaler()
    if df is None or df.empty:
        print(json.dumps({"error": "DataFrame is None or empty in normalize_df"}), file=sys.stderr)
        return df  # Or raise an exception, depending on desired behavior

    if len(df) < window:
        window_df = df
    else:
        window_df = df.tail(window)

    features = ['macd', 'plusDI', 'minusDI', 'ADX', 'close']
    # Check if all features exist in the DataFrame
    for feature in features:
        if feature not in df.columns:
            print(json.dumps({"error": f"Feature '{feature}' missing in DataFrame in normalize_df"}), file=sys.stderr)
            return df  # Or raise an exception

    try:
        # Ensure window_df contains valid data before scaling
        if window_df.empty:
            print(json.dumps({"error": "window_df is empty, cannot normalize"}), file=sys.stderr)
            return df

        # Temporarily store the original index
        original_index = df.index

        # Perform scaling
        df[features] = scaler.fit_transform(pd.concat([window_df[features], df[features]], ignore_index=True))[-len(df):]

        # Restore the original index
        df = df.set_index(original_index)

        # Round normalized features to 2 decimals
        df[features] = df[features].round(2)
    except Exception as e:
        print(json.dumps({"error": f"Error during normalization: {e}"}), file=sys.stderr)
        return df  # Or raise the exception, depending on desired behavior
    return df

def smooth_price(df, window=3):
    """Smooth the 'close' price using a rolling mean."""
    if df is None or df.empty:
        print(json.dumps({"error": "DataFrame is None or empty in smooth_price"}), file=sys.stderr)
        return df
    if 'close' not in df.columns:
        print(json.dumps({"error": "'close' column missing in DataFrame in smooth_price"}), file=sys.stderr)
        return df
    try:
        df['close_smoothed'] = df['close'].rolling(window=window, min_periods=1).mean().round(2)
    except Exception as e:
        print(json.dumps({"error": f"Error during price smoothing: {e}"}), file=sys.stderr)
        return df
    return df

def train_models_on_windows(df, windows=EPOCH_WINDOWS):
    """Train a model for each window size and return predictions."""
    models = {}
    predictions = {}
    if df is None or df.empty:
        print(json.dumps({"error": "DataFrame is None or empty in train_models_on_windows"}), file=sys.stderr)
        return models, predictions

    for win in windows:
        if not isinstance(win, int) or win <= 0:
            print(json.dumps({"error": f"Invalid window size: {win}"}), file=sys.stderr)
            continue

        if len(df) < win:
            print(json.dumps({"warning": f"Not enough data for window size: {win}"}), file=sys.stderr)
            continue  # Not enough data for this window
        try:
            window_df = df.tail(win).copy()
            window_df = normalize_df(window_df, window=15)
            window_df = smooth_price(window_df, window=3)

            # Check if required columns exist after normalization and smoothing
            required_cols = ['macd', 'plusDI', 'minusDI', 'ADX', 'close_smoothed']
            for col in required_cols:
                if col not in window_df.columns:
                    print(json.dumps({"error": f"Required column '{col}' missing in window_df after processing."}), file=sys.stderr)
                    continue  # Skip to the next window

            X = window_df[['macd', 'plusDI', 'minusDI', 'ADX']]
            y = window_df['close_smoothed']

            # Check if X or y is empty
            if X.empty or y.empty:
                print(json.dumps({"error": f"X or y is empty for window size: {win}"}), file=sys.stderr)
                continue

            model = LinearRegression()
            model.fit(X, y)
            models[win] = model
            preds = model.predict(X)
            # Round predictions to 2 decimals
            predictions[win] = [round(float(p), 2) for p in preds]
        except Exception as e:
            print(json.dumps({"error": f"Error training model for window size {win}: {e}"}), file=sys.stderr)

    return models, predictions

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
                models, all_predictions = train_models_on_windows(df)
                signals = generate_signals(df)
                # Store each signal and price in the database
                for i, signal in enumerate(signals):
                    try:
                        price = round(float(df['close'].iloc[i]), 2)
                    except (ValueError, TypeError, IndexError) as e:
                        print(json.dumps({"error": f"Price casting error at index {i}: {e}"}), file=sys.stderr)
                        continue
                    direction = signal
                    try:
                        insert_trade(signal, price, direction)
                    except Exception as e:
                        print(json.dumps({"error": f"DB insert error: {e}"}), file=sys.stderr)
                last_hour_prices = get_first_and_last_price(hours=1)
                last_24h_prices = get_first_and_last_price(hours=24)
                output_data = {
                    'predictions': all_predictions,  # Dict: window_size -> predictions
                    'signals': signals,
                    'originalData': data,
                    'lastHourPrices': last_hour_prices,
                    'last24hPrices': last_24h_prices
                }
                print(json.dumps(output_data))
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)