
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
        # stoch columns are usually k, d, (and maybe j)
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

def detect_chart_patterns(df: pd.DataFrame):
    """
    Experimental detection of chart patterns using local extrema.
    """
    patterns = []
    
    # Need enough data
    if len(df) < 50:
        return patterns
        
    # Find local peaks and troughs
    n = 5 # window size
    df['min'] = df.iloc[argrelextrema(df['Close'].values, np.less_equal, order=n)[0]]['Close']
    df['max'] = df.iloc[argrelextrema(df['Close'].values, np.greater_equal, order=n)[0]]['Close']
    
    # Simple check for simple patterns like Golden Cross recently
    if len(df) > 1:
        last = df.iloc[-1]
        prev = df.iloc[-2]
        if last['SMA_50'] > last['SMA_200'] and prev['SMA_50'] <= prev['SMA_200']:
            patterns.append("Golden Cross")
        if last['SMA_50'] < last['SMA_200'] and prev['SMA_50'] >= prev['SMA_200']:
            patterns.append("Death Cross")
            
    # Advanced: Head and Shoulders (approximation)
    # Looking for Peak A (Shoulder), Peak B (Head, higher), Peak C (Shoulder, lower than Head)
    # This is complex to code reliably without visual check, we will use a simplified logic or placeholder
    # For now, let's stick to Trend Analysis
    
    return patterns

def generate_recommendation(df: pd.DataFrame):
    """
    Generates a Buy/Sell/Neutral recommendation based on scores.
    """
    if df.empty:
        return "NEUTRAL", 50
        
    score = 50
    last = df.iloc[-1]
    
    # RSI Score
    # RSI < 30 -> Oversold (Buy signal) -> +10
    # RSI > 70 -> Overbought (Sell signal) -> -10
    if last['RSI'] < 30: score += 15
    elif last['RSI'] > 70: score -= 15
    elif last['RSI'] > 50: score += 5
    else: score -= 5
    
    # MA Trend
    # Price > SMA200 -> Bullish -> +10
    if last['Close'] > last['SMA_200']: score += 15
    else: score -= 15
    
    # Golden Cross check (recent)
    # (Simplified: if SMA50 > SMA200)
    if 'SMA_50' in df.columns and 'SMA_200' in df.columns:
        if last['SMA_50'] > last['SMA_200']: score += 10
        else: score -= 10
        
    # Cap score
    score = max(0, min(100, score))
    
    if score >= 80: label = "STRONG BUY"
    elif score >= 60: label = "BUY"
    elif score <= 20: label = "STRONG SELL"
    elif score <= 40: label = "SELL"
    else: label = "NEUTRAL"
    
    return label, score
