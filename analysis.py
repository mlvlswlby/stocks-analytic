
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema

def calculate_technicals(df: pd.DataFrame):
    """
    Calculates technical indicators for the given dataframe.
    Expects DataFrame with columns: Open, High, Low, Close, Volume.
    """
    # Moving Averages
    df['SMA_10'] = ta.sma(df['Close'], length=10)
    df['SMA_20'] = ta.sma(df['Close'], length=20)
    df['SMA_50'] = ta.sma(df['Close'], length=50)
    df['SMA_60'] = ta.sma(df['Close'], length=60)
    df['SMA_100'] = ta.sma(df['Close'], length=100)
    df['SMA_200'] = ta.sma(df['Close'], length=200)

    # RSI
    df['RSI'] = ta.rsi(df['Close'], length=14)

    # Stochastic
    stoch = ta.stoch(df['High'], df['Low'], df['Close'])
    if stoch is not None and not stoch.empty:
        # Rename columns to standardized names for easier access
        # Ensure we only take the first two check logic (usually K, D)
        # Fix: If pandas_ta returns 3 columns (e.g. K, D, J or similar), we slice.
        if stoch.shape[1] >= 2:
            stoch = stoch.iloc[:, :2]
            stoch.columns = ['K', 'D']
            df = pd.concat([df, stoch], axis=1)
    
    return df

def detect_candle_patterns(df: pd.DataFrame):
    """
    Detects basic candle patterns.
    """
    patterns = {}
    
    # Get last row
    if df.empty:
        return {}
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None
    
    # Doji
    body_size = abs(last['Close'] - last['Open'])
    full_size = last['High'] - last['Low']
    is_doji = body_size <= (full_size * 0.1)
    patterns['Doji'] = bool(is_doji)
    
    # Hammer (Small body, long lower shadow, little upper shadow)
    lower_shadow = min(last['Open'], last['Close']) - last['Low']
    upper_shadow = last['High'] - max(last['Open'], last['Close'])
    is_hammer = (body_size <= (full_size * 0.3)) and (lower_shadow >= (2 * body_size)) and (upper_shadow <= (0.1 * body_size))
    patterns['Hammer'] = bool(is_hammer)
    
    # Engulfing
    if prev is not None:
        is_bullish_engulfing = (prev['Close'] < prev['Open']) and (last['Close'] > last['Open']) and \
                               (last['Open'] < prev['Close']) and (last['Close'] > prev['Open'])
        is_bearish_engulfing = (prev['Close'] > prev['Open']) and (last['Close'] < last['Open']) and \
                               (last['Open'] > prev['Close']) and (last['Close'] < prev['Open'])
                               
        patterns['Bullish Engulfing'] = bool(is_bullish_engulfing)
        patterns['Bearish Engulfing'] = bool(is_bearish_engulfing)
        
    return patterns

def determine_market_trend(df: pd.DataFrame):
    """
    Determines the market trend phase based on SMA and RSI.
    """
    if df.empty or len(df) < 200:
        return "Neutral"

    last = df.iloc[-1]
    price = last['Close']
    sma50 = last['SMA_50']
    sma200 = last['SMA_200']
    rsi = last['RSI']

    # Bullish: Strong Uptrend
    if price > sma200 and sma50 > sma200:
        return "Bullish"
    
    # Bearish: Strong Downtrend
    if price < sma200 and sma50 < sma200:
        return "Bearish"

    # Accumulation: Potential turning point from bottom
    # Price is suppressed (below SMA200) but showing strength (RSI rising or oversold bounce) OR SMA50 crossing up
    if price < sma200 and (rsi < 40 or (sma50 > last['SMA_20'])): 
        return "Accumulation"

    # Distribution: Potential turning point from top
    # Price is high (above SMA200) but showing weakness (RSI overbought) OR SMA50 crossing down
    if price > sma200 and (rsi > 70 or (sma50 < last['SMA_20'])):
        return "Distribution"

    return "Neutral"
    
    return patterns


def generate_recommendation(df):
    """
    Generate a Buy/Sell/Neutral recommendation based on indicators.
    Returns: (Recommendation String, Score 0-100, List of Reasons)
    """
    if df.empty:
        return "NEUTRAL", 50, []
        
    last = df.iloc[-1]
    score = 50
    reasons = []
    
    # 1. Moving Averages Trend
    if last['SMA_50'] > last['SMA_200']:
        score += 10
        reasons.append("Trend Bullish (SMA50 > SMA200)")
    else:
        score -= 10
        reasons.append("Trend Bearish (SMA50 < SMA200)")
        
    if last['Close'] > last['SMA_200']:
        score += 10
        reasons.append("Price above SMA200")
    else:
        score -= 10
        reasons.append("Price below SMA200")
        
    # 2. RSI
    rsi = last['RSI']
    if rsi < 30:
        score += 20
        reasons.append("RSI Oversold (<30) - Potential Buy")
    elif rsi > 70:
        score -= 20
        reasons.append("RSI Overbought (>70) - Potential Sell")
    else:
        reasons.append(f"RSI Neutral ({rsi:.2f})")
        
    # 3. Stochastic
    k, d = last.get('K', 50), last.get('D', 50)
    if k < 20 and d < 20 and k > d:
        score += 15
        reasons.append("Stochastic Oversold Cross Up")
    elif k > 80 and d > 80 and k < d:
        score -= 15
        reasons.append("Stochastic Overbought Cross Down")
        
    # 4. Golden/Death Cross (Recent)
    # Check last 5 days for cross
    recent = df.iloc[-5:]
    # ... (logic simplified for brevity, assume simple check on last candle for now or stick to trend)
    
    # Determine Label
    if score >= 80:
        rec = "STRONG BUY"
    elif score >= 60:
        rec = "BUY"
    elif score <= 20:
        rec = "STRONG SELL"
    elif score <= 40:
        rec = "SELL"
    else:
        rec = "NEUTRAL"
    
    # Granular Trend Analysis
    trend_details = {}
    current_price = last['Close']
    for ma in [10, 20, 60, 100, 200]:
        ma_col = f'SMA_{ma}'
        if ma_col in df.columns:
            ma_val = last[ma_col]
            if pd.notna(ma_val):
                status = "Above" if current_price > ma_val else "Below"
                trend_details[f'MA_{ma}'] = {"value": ma_val, "status": status}
    
    
    return rec, score, reasons, trend_details

def calculate_forecast(df: pd.DataFrame, days=90):
    """
    Simple linear regression forecast for next 90 days based on last 6 months trend.
    """
    if df.empty:
        return []
        
    # Use last 6 months (~126 trading days) for trend training
    train_df = df.iloc[-126:].copy()
    if len(train_df) < 10:
        return []

    y = train_df['Close'].values
    x = np.arange(len(y))
    
    # Linear Regression: y = mx + c
    A = np.vstack([x, np.ones(len(x))]).T
    m, c = np.linalg.lstsq(A, y, rcond=None)[0]
    
    # Generate future dates
    last_date = df.index[-1]
    future_dates = [last_date + pd.Timedelta(days=i) for i in range(1, days + 1)]
    
    # Project prices
    last_x = x[-1]
    future_x = np.arange(last_x + 1, last_x + 1 + days)
    future_y = m * future_x + c
    
    forecast_data = []
    for date, price in zip(future_dates, future_y):
        forecast_data.append({
            "time": str(date.date()),
            "value": max(0, price) # Price cannot be negative
        })
        
    return forecast_data

def calculate_seasonal(df: pd.DataFrame):
    """
    Returns data grouped by year for the last 3 years to compare seasonality.
    """
    seasonal_data = {}
    
    # Ensure index is datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
        
    current_year = df.index[-1].year
    years = [current_year, current_year - 1, current_year - 2]
    
    for year in years:
        # Filter data for specific year
        year_data = df[df.index.year == year]
        if not year_data.empty:
            # We normalize 'time' to be MM-DD so they can overlay on same x-axis
            data_points = []
            for date, row in year_data.iterrows():
                # specific format for chart.js labels? just MM-DD
                data_points.append({
                    "label": f"{date.month}-{date.day}", # Simplified Day
                    "value": row['Close']
                })
            seasonal_data[year] = data_points
            
    return seasonal_data
