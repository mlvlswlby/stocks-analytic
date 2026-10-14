
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
    
    # Filter levels relevant to the input Average Price
    # Nearest Resistance ABOVE the average price (so it's actually a profit)
    upper_levels = [r for r in resistances if r > avg_price * 1.01] # 1% buffer over avg_price
    # Nearest Support BELOW the average price
    lower_levels = [s for s in supports if s < avg_price * 0.99] # 1% buffer under avg_price
    
    # Define Targets
    tp_list = list(upper_levels[:5])  # Cap at max 5 historical resistances above purchase price
    
    if not tp_list:
        # If no historical ceilings above purchase price, calculate Fibonacci Extensions
        recent_high = window['High'].max()
        recent_low = window['Low'].min()
        diff = recent_high - recent_low
        
        # Prevent zero-variance failure
        if diff <= 0:
            diff = avg_price * 0.10
            
        # Standard Fibonacci Extension cluster multiples
        fib_multiples = [1.618, 2.618, 3.618, 4.236, 5.236, 6.236, 7.236]
        fib_levels = [recent_low + (diff * m) for m in fib_multiples]
        
        # Filter Fib levels that are strictly higher than avg_price
        tp_list = [f for f in fib_levels if f > avg_price * 1.01][:5]
        
        if not tp_list:
            # Mathematical safety net
            tp_list = [avg_price * 1.05, avg_price * 1.10, avg_price * 1.15]
            
    # For Cut Loss, take the nearest local support below the purchase price
    cl = lower_levels[-1] if len(lower_levels) > 0 else avg_price * 0.95
    if cl >= avg_price: cl = avg_price * 0.95
    
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
            "tp_list": tp_list,
            "cl": cl
        }
    }

def generate_entry_plan(df: pd.DataFrame):
    """
    Generates a trading plan specifically for BUYING at the current price.
    Purely technical analysis (price action, chart patterns, support/resistance, Fibonacci).
    Returns: TP targets, CL limit, RR ratio, Candlestick patterns, and Entry Status.
    """
    if df.empty:
        return {}

    last = df.iloc[-1]
    current_price = float(last['Close'])
    
    # Identify market phase
    trend = determine_market_trend(df)
    candle_patterns = detect_candle_patterns(df)
    active_patterns = [name for name, present in candle_patterns.items() if present]
    
    # Calculate Support & Resistance for the last 6 months (~126 trading days)
    window = df.iloc[-126:].copy()
    
    # Adaptive order to prevent crash on small dataframes
    order_val = min(5, max(1, len(window) // 6)) if len(window) >= 4 else 1
    
    try:
        res_indices = argrelextrema(window['High'].values, np.greater, order=order_val)[0]
        sup_indices = argrelextrema(window['Low'].values, np.less, order=order_val)[0]
        resistances = window['High'].iloc[res_indices].sort_values(ascending=True).values
        supports = window['Low'].iloc[sup_indices].sort_values(ascending=True).values
    except Exception:
        resistances = np.array([])
        supports = np.array([])
    
    # Take Profit levels must be above current price (+1% minimum)
    upper_levels = [float(r) for r in resistances if r > current_price * 1.01] 
    # Cut Loss levels must be below current price (-1% minimum)
    lower_levels = [float(s) for s in supports if s < current_price * 0.99]
    
    tp_list = list(upper_levels[:5])
    
    # If no structural resistance above, project target via Fibonacci extensions
    if not tp_list:
        recent_high = float(window['High'].max())
        recent_low = float(window['Low'].min())
        diff = recent_high - recent_low
        if diff <= 0: 
            diff = current_price * 0.10
        
        fib_multiples = [1.618, 2.618, 3.618, 4.236]
        fib_levels = [recent_low + (diff * m) for m in fib_multiples]
        tp_list = [float(f) for f in fib_levels if f > current_price * 1.01][:5]
        if not tp_list:
            tp_list = [current_price * 1.05, current_price * 1.10, current_price * 1.15]
            
    # Stop Loss on nearest key support level
    cl = float(lower_levels[-1]) if len(lower_levels) > 0 else (current_price * 0.95)
    if cl >= current_price or cl <= 0:
        cl = current_price * 0.95
    
    # Assess Entry Status based purely on structure/trend & candlestick patterns
    setup_status = "GOOD SETUP"
    setup_color = "emerald"
    reason = "Market trend is supportive for long positions."
    
    pattern_note = f" (Pola candlestick: {', '.join(active_patterns)})" if active_patterns else ""
    
    if trend in ["Bearish", "Distribution"]:
        setup_status = "HIGH RISK / DO NOT BUY"
        setup_color = "rose"
        reason = f"Saham ini terlalu risky untuk dibeli saat ini karena sedang berada dalam fase {trend}. Membeli sekarang berisiko pisau jatuh. Tetap disediakan Trading Plan (TP & SL) di bawah ini sebagai acuan teknikal.{pattern_note}"
    elif trend == "Neutral":
        setup_status = "NEUTRAL SETUP"
        setup_color = "slate"
        reason = f"Pergerakan harga saat ini sideways / netral tanpa konfirmasi arah yang kuat. Disarankan menunggu sinyal konfirmasi breakout.{pattern_note}"
    elif trend == "Accumulation":
        setup_status = "GREAT SETUP (BOTTOM FISHING)"
        setup_color = "teal"
        reason = f"Harga berada di area akumulasi bawah (bottoming) dengan potensi reward yang menarik relatif terhadap risiko.{pattern_note}"
        
    # Calculate basic Risk/Reward Ratio using the first TP
    risk = current_price - cl
    reward = tp_list[0] - current_price if tp_list else 0
    rr_ratio = float(reward / risk) if risk > 0 else 0.0
    
    if rr_ratio < 1.0 and trend not in ["Bearish", "Distribution"]:
         setup_status = "POOR RISK/REWARD"
         setup_color = "amber"
         reason = f"Trend teknikal cukup baik, namun potensi profit ke resisten terdekat ({round(tp_list[0], 2)}) lebih kecil dibanding batas risiko cut loss ({round(cl, 2)}). R/R kurang optimal.{pattern_note}"
    
    # Clean rounding
    tp_list_clean = [round(float(tp), 2) for tp in tp_list]
    cl_clean = round(float(cl), 2)
    current_price_clean = round(float(current_price), 2)
    
    tp1 = tp_list_clean[0] if tp_list_clean else round(current_price * 1.05, 2)
    tp2 = tp_list_clean[1] if len(tp_list_clean) > 1 else None

    # --- TACTICAL BEST SETUP: Target Price for Entry (Support Retest / Pullback) ---
    s1 = float(lower_levels[-1]) if len(lower_levels) > 0 else None
    s2 = float(lower_levels[-2]) if len(lower_levels) > 1 else None
    
    if s1:
        dist_pct = (current_price - s1) / current_price * 100.0
        if dist_pct <= 1.5:
            # Price is already resting right at key support
            best_entry = current_price
            strategy_label = "Buy on Support"
            is_pullback = False
        else:
            # Price has extended away; optimal entry is to wait for pullback to support
            best_entry = s1
            strategy_label = "Buy on Pullback / Retest Support"
            is_pullback = True
            
        # Cut Loss for best setup placed just under support
        if s2 and s2 >= s1 * 0.92:
            best_cl = round(s2 * 0.99, 2)
        else:
            best_cl = round(best_entry * 0.97, 2)
    else:
        best_entry = round(current_price * 0.96, 2)
        best_cl = round(best_entry * 0.96, 2)
        strategy_label = "Buy on Pullback Discount"
        is_pullback = True

    if best_cl >= best_entry:
        best_cl = round(best_entry * 0.96, 2)

    target_entry_clean = round(float(best_entry), 2)
    target_cl_clean = round(float(best_cl), 2)
    best_tp1 = tp1
    best_tp2 = tp2

    # Asymmetric Risk/Reward Ratio for Best Setup
    bs_risk = target_entry_clean - target_cl_clean
    bs_reward = best_tp1 - target_entry_clean
    best_rr = round(bs_reward / bs_risk, 2) if bs_risk > 0 else 0.0

    # Actionable Formulated Description
    if trend in ["Bearish", "Distribution"]:
        best_setup_desc = (
            f"Saham sedang dalam fase {trend}. Hindari membeli langsung di harga sekarang ({current_price_clean})! "
            f"Best Setup: Disarankan menunggu antri beli ketika harga menyentuh support di Rp {target_entry_clean}. "
            f"Selama harga bertahan di atas Cut Loss Rp {target_cl_clean}, potensi pantulan teknikal menuju TP 1 Rp {best_tp1}"
            f"{f' dan TP 2 Rp {best_tp2}' if best_tp2 else ''} terbuka dengan Risk/Reward {best_rr}x. Wajib Cut Loss jika tembus di bawah Rp {target_cl_clean}."
        )
    elif is_pullback:
        best_setup_desc = (
            f"Best Setup ({strategy_label}): Harga saat ini ({current_price_clean}) sudah naik di atas support. "
            f"Disarankan jangan mengejar harga, melainkan tunggu atau antri beli pada target harga Rp {target_entry_clean} (area support terdekat). "
            f"Selama harga mampu bertahan di atas batas Cut Loss Rp {target_cl_clean}, potensi kenaikan menuju TP 1 Rp {best_tp1}"
            f"{f' hingga TP 2 Rp {best_tp2}' if best_tp2 else ''} sangat optimal dengan Risk/Reward {best_rr}x."
        )
    else:
        best_setup_desc = (
            f"Best Setup ({strategy_label}): Harga saat ini ({current_price_clean}) sudah berada tepat di bantalan support kuat. "
            f"Disarankan entry beli di target harga Rp {target_entry_clean}. "
            f"Selama harga bertahan di atas batas Cut Loss Rp {target_cl_clean}, potensi kenaikan menuju TP 1 Rp {best_tp1}"
            f"{f' hingga TP 2 Rp {best_tp2}' if best_tp2 else ''} sangat menjanjikan dengan Risk/Reward {best_rr}x."
        )

    return {
        "current_price": current_price_clean,
        "status": setup_status,
        "color": setup_color,
        "reason": reason,
        "rr_ratio": round(rr_ratio, 2),
        "patterns": active_patterns,
        "best_setup": {
            "strategy": strategy_label,
            "entry_target": target_entry_clean,
            "cl_target": target_cl_clean,
            "tp_target": best_tp1,
            "tp_secondary": best_tp2,
            "best_rr": best_rr,
            "is_pullback": is_pullback,
            "description": best_setup_desc
        },
        "targets": {
            "tp_list": tp_list_clean,
            "cl": cl_clean
        }
    }
