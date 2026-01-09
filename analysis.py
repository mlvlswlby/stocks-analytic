
import pandas as pd
import pandas_ta as ta
import numpy as np

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

def detect_chart_patterns(df: pd.DataFrame):
    """
    Detects overall chart patterns and market structure on Daily timeframe.
    Priority: Geometric Patterns > High/Low > Market State (Consolidation/Sideways).
    """
    patterns = []
    
    if df.empty or len(df) < 50:
        return ["Insufficient Data"]
        
    last = df.iloc[-1]
    close = df['Close']
    high = df['High']
    low = df['Low']
    
    # 1. 52-Week High/Low (approx 252 trading days)
    # We might not have 252 days in 'df' if not requested, but let's check what we have.
    lookback = min(len(df), 252)
    recent_high = high.iloc[-lookback:].max()
    recent_low = low.iloc[-lookback:].min()
    
    threshold = 0.02 # 2% form high/low
    if last['Close'] >= recent_high * (1 - threshold):
        patterns.append("Near 52-Week High")
    elif last['Close'] <= recent_low * (1 + threshold):
        patterns.append("Near 52-Week Low")
        
    # 2. Trend / Channel Analysis (Linear Regression Slope)
    # Check last 20 days (approx 1 month)
    
    window = 20
    if len(df) >= window:
        y = close.iloc[-window:].values
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        # Normalize slope by price to get percentage
        norm_slope = slope / last['Close']
        
        if norm_slope > 0.005: # > 0.5% per day rise approx
            patterns.append("Uptrend Channel")
        elif norm_slope < -0.005:
            patterns.append("Downtrend Channel")
            
    # 3. Volatility / Consolidation (Bollinger Bandwidth)
    # BB Width = (Upper - Lower) / Middle
    # Assuming we calculated BB earlier or can calc here? 
    # Let's rely on standard deviation of last 20 days relative to price
    volatility = close.iloc[-20:].std() / close.iloc[-20:].mean()
    
    # If volatility is very low, it's Consolidation/Sideways
    if volatility < 0.015: # 1.5% std dev
        patterns.append("Consolidation / Sideways")
    
    # If no specific patterns found and not consolidation, maybe just "Normal Volatility" or skip
    # But user asked: "if not formed pattern, check consolidation/distribution/sideways"
    
    # If we detected a Trend, we don't say Sideways.
    # If we didn't detect Trend or High/Low, we default to Market State.
    
    has_trend = any(p in patterns for p in ["Uptrend Channel", "Downtrend Channel"])
    
    if not has_trend and "Consolidation / Sideways" not in patterns:
        # Check usually distribution is high volatility sideways? 
        # For simplicity, if not trending, we call it "Sideways" or "Range Bound"
        patterns.append("Sideways / Range Bound")

    # ... (Previous code: 52-Week, Channel, Volatility preserved) ... Do not delete them, just APPEND.
    # To keep this clean, I will rewrite the function content to include them properly.
    
    # 4. Local Extrema Analysis for Geometric Patterns
    # Find peaks and troughs over last 60 days
    n = 3 # sensitivity for extrema
    df['min'] = df.iloc[argrelextrema(df['Close'].values, np.less_equal, order=n)[0]]['Close']
    df['max'] = df.iloc[argrelextrema(df['Close'].values, np.greater_equal, order=n)[0]]['Close']
    
    # Extract last few peaks and troughs
    last_60 = df.iloc[-60:].copy()
    peaks = last_60[last_60['max'].notna()]['max']
    troughs = last_60[last_60['min'].notna()]['min']
    
    # Need at least 3 peaks/troughs for complex patterns
    if len(peaks) >= 3 and len(troughs) >= 3:
        p1, p2, p3 = peaks.iloc[-3], peaks.iloc[-2], peaks.iloc[-1]
        t1, t2, t3 = troughs.iloc[-3], troughs.iloc[-2], troughs.iloc[-1]
        
        # --- Head & Shoulders ---
        # Peak 2 (Head) significantly higher than P1, P3 (Shoulders)
        if p2 > p1 * 1.02 and p2 > p3 * 1.02 and abs(p1 - p3) < (p1 * 0.05):
            patterns.append("Head & Shoulders")
            
        # --- Inverse Head & Shoulders ---
        if t2 < t1 * 0.98 and t2 < t3 * 0.98 and abs(t1 - t3) < (t1 * 0.05):
            patterns.append("Inv. Head & Shoulders")
            
        # --- Double Top ---
        # Two most recent peaks similar height
        if abs(p3 - p2) < (p3 * 0.02) and p3 > p1: 
             patterns.append("Double Top")
             
        # --- Double Bottom ---
        if abs(t3 - t2) < (t3 * 0.02) and t3 < t1:
             patterns.append("Double Bottom")
             
        # --- Triangles (based on slope of peaks/troughs) ---
    # 2. Trend / Channel Analysis (Linear Regression Slope)
    # Check last 20 days (approx 1 month)
    
    window = 20
    if len(df) >= window:
        y = close.iloc[-window:].values
        x = np.arange(len(y))
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        # Normalize slope by price to get percentage
        norm_slope = slope / last['Close']
        
        if norm_slope > 0.005: # > 0.5% per day rise approx
            patterns.append("Uptrend Channel")
        elif norm_slope < -0.005:
            patterns.append("Downtrend Channel")
            patterns.append("Symmetrical Triangle")
            
        # Ascending: Highs flat, Lows up
        elif abs(p1 - p3) < (p1 * 0.015) and t1 < t2 < t3:
            patterns.append("Ascending Triangle")
            
        # Descending: Highs down, Lows flat
        elif p1 > p2 > p3 and abs(t1 - t3) < (t1 * 0.015):
             patterns.append("Descending Triangle")
             
        # --- Wedges ---
        # Falling Wedge: Highs down, Lows down (converging? implies slope diff)
        elif p1 > p2 > p3 and t1 > t2 > t3:
            # Check convergence: Slope of highs steeper than lows?
            patterns.append("Falling Wedge") # Simplified
            
        # Rising Wedge
        elif p1 < p2 < p3 and t1 < t2 < t3:
             patterns.append("Rising Wedge")
             
        # --- Rectangles ---
        # Highs flat, Lows flat
        elif abs(p1 - p3) < (p1 * 0.015) and abs(t1 - t3) < (t1 * 0.015):
            # Check trend to decide Bullish/Bearish
            if last['SMA_50'] > last['SMA_200']:
                patterns.append("Bullish Rectangle")
            else:
                patterns.append("Bearish Rectangle")
                
    # --- Pennants (Short term triangle after sharp move) ---
    # Check sharp move in last 10 days
    recent_move = (df['Close'].iloc[-1] - df['Close'].iloc[-10]) / df['Close'].iloc[-10]
    if abs(recent_move) > 0.10: # >10% move
        # Check consolidation (low volatility) now
        if volatility < 0.02:
            if recent_move > 0:
                patterns.append("Bullish Pennant")
            else:
                patterns.append("Bearish Pennant")
                
    # --- Cup and Handle ---
    # Complex shapes. Heuristic: Price below 52wk high but recovering.
    # Long rounded bottom? Hard with just extrema.
    # Simplified: Look for U-shape recovery to near high, then small dip.
    # (Leaving as placeholder or simple proximity check)
    if "Near 52-Week High" in patterns and "Consolidation / Sideways" in patterns:
        patterns.append("Cup & Handle Potential")
        
    return list(set(patterns)) # Unique

def generate_recommendation(df: pd.DataFrame):
    """
    Generate a Buy/Sell/Neutral recommendation based on indicators.
    Returns: (Recommendation String, Score 0-100, List of Reasons, Trend Details)
    """
    if df.empty:
        return "NEUTRAL", 50, [], {}
        
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
