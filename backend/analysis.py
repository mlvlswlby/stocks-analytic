
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

def generate_trade_plan(df: pd.DataFrame, avg_price: float, buy_date: str = None):
    """
    Generates a trade plan (TP, CL, Action) based on average price and current technicals.
    """
    if df.empty:
        return {}

    last = df.iloc[-1]
    current_price = last['Close']
    
    # Calculate P/L
    pl_pct = ((current_price - avg_price) / avg_price) * 100
    
    # Identify market phase
    trend = determine_market_trend(df)
    
    # Support & Resistance (Simple Local Extrema)
    # Get last 6 months for Support/Resistance
    window = df.iloc[-126:].copy()
    
    # Find peaks (Resistance) and troughs (Support)
    # order=5 means local max/min over 10 days window (5 each side)
    res_indices = argrelextrema(window['High'].values, np.greater, order=5)[0]
    sup_indices = argrelextrema(window['Low'].values, np.less, order=5)[0]
    
    resistances = window['High'].iloc[res_indices].sort_values(ascending=True).values
    supports = window['Low'].iloc[sup_indices].sort_values(ascending=True).values
    
    # Filter levels relevant to current price
    # Nearest Resistance above current price
    upper_levels = [r for r in resistances if r > current_price * 1.01] # 1% buffer
    # Nearest Support below current price
    lower_levels = [s for s in supports if s < current_price * 0.99] # 1% buffer
    
    # Define Targets
    tp1 = upper_levels[0] if len(upper_levels) > 0 else current_price * 1.05
    tp2 = upper_levels[1] if len(upper_levels) > 1 else (tp1 * 1.05)
    tp3 = upper_levels[2] if len(upper_levels) > 2 else (tp2 * 1.05)
    
    cl = lower_levels[-1] if len(lower_levels) > 0 else current_price * 0.95
    
    # sanity checks
    if tp1 <= current_price: tp1 = current_price * 1.05
    if cl >= current_price: cl = current_price * 0.95
    
    # Action Logic
    action = "HOLD"
    reason = "Market condition supports holding."
    
    # Logic Matrix
    if pl_pct > 0:
        # Profitable Position
        if trend in ["Bearish", "Distribution"]:
            action = "TAKE PROFIT"
            reason = "Trend is weakening/bearish. Secure your gains."
        elif trend == "Bullish":
            action = "HOLD"
            reason = "Trend is Bullish. Let your profit run."
        elif trend == "Accumulation":
            action = "HOLD"
            reason = "Price is stabilizing. Hold specific positions."
            
        # High Profit Alert
        if pl_pct > 25:
             action += " (Partially)"
             reason += " Consider taking partial profit at this high level."
             
    else:
        # Losing Position
        if trend == "Bearish":
            action = "CUT LOSS"
            reason = "Trend is Bearish. Minimize further losses."
        elif trend == "Distribution":
            action = "CUT LOSS"
            reason = "Distribution phase detected (Market Top). Exit now."
        elif trend == "Accumulation":
            action = "AVERAGE DOWN"
            reason = "Price is in accumulation zone. Consider buying more."
        elif trend == "Bullish":
            # Correction in Uptrend
            if pl_pct > -7:
                action = "HOLD"
                reason = "Minor pullback in Bullish trend."
            else:
                action = "CUT LOSS"
                reason = "Loss exceeds risk threshold (-7%) despite trend."

    return {
        "current_price": current_price,
        "avg_price": avg_price,
        "pl_pct": pl_pct,
        "action": action,
        "reason": reason,
        "market_trend": trend,
        "targets": {
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "cl": cl
        }
    }
