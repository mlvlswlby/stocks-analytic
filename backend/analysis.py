
import pandas as pd
import pandas_ta as ta
import numpy as np
from scipy.signal import argrelextrema
import math

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

def is_idx_symbol(ticker: str = None) -> bool:
    """Detects whether a ticker belongs to the Indonesian Stock Exchange (IDX)."""
    if not ticker:
        return False
    t = str(ticker).strip().upper()
    if t.endswith(".JK") or t.endswith(".ID"):
        return True
    clean = t.replace(".JK", "")
    if len(clean) == 4 and clean.isalpha():
        US_COMMON = {
            "AAPL", "MSFT", "GOOG", "NVDA", "META", "AMZN", "INTC", "TSLA",
            "NFLX", "AMD", "QCOM", "AVGO", "CSCO", "PYPL", "ADBE", "CMCSA", "PEP", "COST"
        }
        if clean not in US_COMMON:
            return True
    return False

def round_to_market_tick(price: float, is_idx: bool = False) -> float:
    """
    Rounds prices to legitimate market tick fractions:
    - For IDX: Follows official Bursa Efek Indonesia (BEI) discrete tick fractions.
    - For US / Global: Standard currency cents (2 decimal places).
    """
    if price is None or math.isnan(price) or price <= 0:
        return price
    if not is_idx:
        return round(float(price), 2)
    
    # Official BEI / IDX Fraksi Harga:
    # < 200: Rp 1
    # 200 - < 500: Rp 2
    # 500 - < 2000: Rp 5
    # 2000 - < 5000: Rp 10
    # >= 5000: Rp 25
    if price < 200:
        tick = 1.0
    elif price < 500:
        tick = 2.0
    elif price < 2000:
        tick = 5.0
    elif price < 5000:
        tick = 10.0
    else:
        tick = 25.0
    return float(round(price / tick) * tick)

def cluster_support_resistance(df: pd.DataFrame, current_price: float, is_idx: bool = False, window_days: int = 150):
    """
    Identifies significant support and resistance zones using multi-touch swing highs and lows,
    incorporating the Polarity Principle (broken supports become resistances),
    and clusters nearby levels within a 3.0% threshold into consolidated key price zones with touch counts.
    Returns: (supports: list, resistances: list, s1: float, s2: float)
    """
    if df.empty or len(df) < 5:
        s1 = round_to_market_tick(current_price * 0.95, is_idx)
        s2 = round_to_market_tick(current_price * 0.90, is_idx)
        return [], [], s1, s2

    window = df.iloc[-min(window_days, len(df)):].copy()
    highs = window['High'].values
    lows = window['Low'].values
    
    raw_levels = []
    
    # Multi-order extrema detection (macro swings order=5, micro swings order=3)
    orders = [5, 3] if len(window) >= 30 else [max(1, len(window) // 6)]
    for ord_val in orders:
        if len(window) > ord_val * 2:
            try:
                res_idx = argrelextrema(highs, np.greater, order=ord_val)[0]
                sup_idx = argrelextrema(lows, np.less, order=ord_val)[0]
                for idx in res_idx:
                    raw_levels.append({"price": float(highs[idx]), "type": "high", "weight": ord_val})
                for idx in sup_idx:
                    raw_levels.append({"price": float(lows[idx]), "type": "low", "weight": ord_val})
            except Exception:
                pass
                
    # Add absolute extremes of the window
    raw_levels.append({"price": float(np.nanmax(highs)), "type": "high", "weight": 5})
    raw_levels.append({"price": float(np.nanmin(lows)), "type": "low", "weight": 5})
    
    # Filter out NaNs and non-positive prices
    raw_levels = [item for item in raw_levels if item["price"] > 0 and not np.isnan(item["price"])]
    raw_levels.sort(key=lambda x: x["price"])
    
    # Cluster nearby levels within 3.0% threshold
    clusters = []
    threshold = 0.03
    for item in raw_levels:
        p = item["price"]
        added = False
        for c in clusters:
            center = sum(x["price"] for x in c["items"]) / len(c["items"])
            if abs(p - center) / center <= threshold:
                c["items"].append(item)
                added = True
                break
        if not added:
            clusters.append({"items": [item]})

    consolidated = []
    for c in clusters:
        prices = [x["price"] for x in c["items"]]
        touches = len(c["items"])
        avg_p = sum(prices) / len(prices)
        if avg_p >= current_price:
            rep = max(prices)  # ceiling / resistance zone boundary
        else:
            rep = min(prices)  # floor / support zone boundary
        rep_tick = round_to_market_tick(rep, is_idx)
        consolidated.append({
            "rep_price": rep_tick,
            "touches": touches,
            "min": min(prices),
            "max": max(prices)
        })

    # Separate into supports and resistances
    # Support must be below current price (buffer of at least 1%)
    supports = [c for c in consolidated if c["rep_price"] < current_price * 0.99]
    supports.sort(key=lambda x: x["rep_price"], reverse=True) # Nearest support first

    # Resistance must be above current price (buffer of at least 1.5%)
    resistances = [c for c in consolidated if c["rep_price"] > current_price * 1.015]
    resistances.sort(key=lambda x: x["rep_price"]) # Nearest resistance first

    # Determine Primary Support (s1) and Secondary Support (s2)
    s1 = supports[0]["rep_price"] if supports else round_to_market_tick(current_price * 0.95, is_idx)
    s2 = supports[1]["rep_price"] if len(supports) > 1 else round_to_market_tick(s1 * 0.95, is_idx)

    return supports, resistances, s1, s2

def build_take_profit_levels(resistances: list, current_price: float, s1: float, window_high: float, is_idx: bool = False, min_spacing: float = 0.035) -> list:
    """
    Builds a list of 5 well-spaced, progressive Take Profit targets.
    Guarantees that each consecutive TP is at least min_spacing (3.5%+) above the previous one,
    eliminating redundant close targets (e.g. 438 and 440).
    If there are fewer than 5 structural resistance zones, expands with Fibonacci extensions.
    """
    tp_list = []
    for r in resistances:
        cand = r["rep_price"]
        if not tp_list:
            if cand >= current_price * 1.02:
                tp_list.append(cand)
        else:
            prev_tp = tp_list[-1]
            if (cand - prev_tp) / prev_tp >= min_spacing:
                tp_list.append(cand)
                
    # Expand with Fibonacci extensions if less than 5 targets
    if len(tp_list) < 5:
        ref_high = max(window_high, (tp_list[-1] if tp_list else current_price))
        diff = ref_high - s1
        if diff <= 0:
            diff = current_price * 0.15
            
        fib_ratios = [1.272, 1.414, 1.618, 2.0, 2.618]
        for f in fib_ratios:
            if len(tp_list) >= 5:
                break
            proj = round_to_market_tick(s1 + (diff * f), is_idx)
            last_tp = tp_list[-1] if tp_list else current_price
            if (proj - last_tp) / last_tp >= min_spacing and proj > current_price * 1.02:
                tp_list.append(proj)
                
    # If still less than 5, use percentage expansion
    pct_steps = [0.05, 0.10, 0.15, 0.22, 0.30, 0.40, 0.50]
    for step in pct_steps:
        if len(tp_list) >= 5:
            break
        proj = round_to_market_tick(current_price * (1 + step), is_idx)
        last_tp = tp_list[-1] if tp_list else current_price
        if (proj - last_tp) / last_tp >= min_spacing:
            tp_list.append(proj)
            
    # Return exactly top 5, sorted ascending
    tp_list.sort()
    return tp_list[:5]

def generate_trade_plan(df: pd.DataFrame, avg_price: float, buy_date: str = None, ticker: str = None):
    """
    Generates a trade plan (TP, CL, Action) based on average price and current technicals.
    Uses multi-touch support/resistance clustering and progressive spacing for TP.
    """
    if df.empty:
        return {}

    is_idx = is_idx_symbol(ticker)
    last = df.iloc[-1]
    current_price = float(last['Close'])
    current_price_clean = round_to_market_tick(current_price, is_idx)
    avg_price_clean = round_to_market_tick(avg_price, is_idx)
    
    # Calculate P/L
    pl_pct = ((current_price - avg_price) / avg_price) * 100
    
    # Identify market phase
    trend = determine_market_trend(df)
    
    # Identify Support & Resistance Clusters
    supports, resistances, s1, s2 = cluster_support_resistance(df, current_price, is_idx=is_idx)
    window_high = float(df.iloc[-150:]['High'].max()) if len(df) >= 150 else float(df['High'].max())
    
    # Take Profit targets strictly above both avg_price and current_price (or base reference)
    base_ref = max(avg_price, current_price)
    tp_list = build_take_profit_levels(resistances, base_ref, s1, window_high, is_idx=is_idx)
    
    # Cut loss: nearest strong support below purchase price
    lower_supports = [s["rep_price"] for s in supports if s["rep_price"] < avg_price * 0.99]
    cl = lower_supports[0] if lower_supports else round_to_market_tick(avg_price * 0.95, is_idx)
    if cl >= avg_price or cl <= 0:
        cl = round_to_market_tick(avg_price * 0.95, is_idx)
    
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
        "current_price": current_price_clean,
        "avg_price": avg_price_clean,
        "pl_pct": round(pl_pct, 2),
        "action": action,
        "reason": reason,
        "market_trend": trend,
        "targets": {
            "tp_list": tp_list,
            "cl": cl
        }
    }

def generate_entry_plan(df: pd.DataFrame, ticker: str = None):
    """
    Generates a trading plan specifically for BUYING at the current price.
    Purely technical analysis (price action, chart patterns, support/resistance clustering, Fibonacci).
    Returns: TP targets, CL limit, RR ratio, Candlestick patterns, and Tactical Best Setup.
    """
    if df.empty:
        return {}

    is_idx = is_idx_symbol(ticker)
    last = df.iloc[-1]
    current_price = float(last['Close'])
    current_price_clean = round_to_market_tick(current_price, is_idx)
    
    # Identify market phase & candle patterns
    trend = determine_market_trend(df)
    candle_patterns = detect_candle_patterns(df)
    active_patterns = [name for name, present in candle_patterns.items() if present]
    
    # Calculate Support & Resistance clusters
    supports, resistances, s1, s2 = cluster_support_resistance(df, current_price, is_idx=is_idx)
    window_high = float(df.iloc[-150:]['High'].max()) if len(df) >= 150 else float(df['High'].max())
    
    # Build Take Profit levels with progressive minimum distance
    tp_list = build_take_profit_levels(resistances, current_price, s1, window_high, is_idx=is_idx)
    
    # Stop Loss placed just below key primary support level (s1)
    cl = round_to_market_tick(s1 * 0.97, is_idx)
    if cl >= current_price or cl <= 0:
        cl = round_to_market_tick(current_price * 0.95, is_idx)
    
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
    risk = current_price_clean - cl
    reward = tp_list[0] - current_price_clean if tp_list else 0
    rr_ratio = float(reward / risk) if risk > 0 else 0.0
    
    if rr_ratio < 1.0 and trend not in ["Bearish", "Distribution"]:
         setup_status = "POOR RISK/REWARD"
         setup_color = "amber"
         reason = f"Trend teknikal cukup baik, namun potensi profit ke resisten terdekat ({tp_list[0]}) lebih kecil dibanding batas risiko cut loss ({cl}). R/R kurang optimal.{pattern_note}"
    
    tp1 = tp_list[0] if tp_list else round_to_market_tick(current_price * 1.05, is_idx)
    tp2 = tp_list[1] if len(tp_list) > 1 else None

    # --- TACTICAL BEST SETUP: Target Price for Entry (Support Retest / Pullback) ---
    dist_to_s1_pct = (current_price - s1) / current_price * 100.0 if current_price > 0 else 0
    if dist_to_s1_pct <= 1.5 and dist_to_s1_pct >= -1.0:
        # Price is already resting right at key support
        best_entry = current_price_clean
        strategy_label = "Buy on Support"
        is_pullback = False
        best_cl = round_to_market_tick(s1 * 0.97, is_idx)
    else:
        # Price has extended away; optimal entry is to wait for pullback to key support
        best_entry = s1
        strategy_label = "Buy on Pullback / Retest Support"
        is_pullback = True
        best_cl = round_to_market_tick(s1 * 0.97, is_idx)
        
    if best_cl >= best_entry:
        best_cl = round_to_market_tick(best_entry * 0.96, is_idx)

    target_entry_clean = round_to_market_tick(best_entry, is_idx)
    target_cl_clean = round_to_market_tick(best_cl, is_idx)
    best_tp1 = tp1
    best_tp2 = tp2

    # Asymmetric Risk/Reward Ratio for Best Setup
    bs_risk = target_entry_clean - target_cl_clean
    bs_reward = best_tp1 - target_entry_clean
    best_rr = round(bs_reward / bs_risk, 2) if bs_risk > 0 else 0.0

    # Format numbers for readable text descriptions
    def fmt_price(val):
        if is_idx:
            return f"Rp {int(val):,}".replace(",", ".")
        return f"${val:,.2f}"

    curr_p_str = fmt_price(current_price_clean)
    entry_p_str = fmt_price(target_entry_clean)
    cl_p_str = fmt_price(target_cl_clean)
    tp1_str = fmt_price(best_tp1)
    tp2_str = f" dan TP 2 {fmt_price(best_tp2)}" if best_tp2 else ""

    # Actionable Formulated Description
    if trend in ["Bearish", "Distribution"]:
        best_setup_desc = (
            f"Saham sedang dalam fase {trend}. Hindari membeli langsung di harga sekarang ({curr_p_str})! "
            f"Best Setup: Disarankan menunggu antri beli ketika harga menyentuh support kuat di {entry_p_str}. "
            f"Selama harga bertahan di atas Cut Loss {cl_p_str}, potensi pantulan teknikal menuju TP 1 {tp1_str}"
            f"{tp2_str} terbuka dengan Risk/Reward {best_rr}x. Wajib Cut Loss jika tembus di bawah {cl_p_str}."
        )
    elif is_pullback:
        best_setup_desc = (
            f"Best Setup ({strategy_label}): Harga saat ini ({curr_p_str}) sudah naik di atas support. "
            f"Disarankan jangan mengejar harga, melainkan tunggu atau antri beli pada target harga {entry_p_str} (area support kuat). "
            f"Selama harga mampu bertahan di atas batas Cut Loss {cl_p_str}, potensi kenaikan menuju TP 1 {tp1_str}"
            f"{f' hingga TP 2 {fmt_price(best_tp2)}' if best_tp2 else ''} sangat optimal dengan Risk/Reward {best_rr}x."
        )
    else:
        best_setup_desc = (
            f"Best Setup ({strategy_label}): Harga saat ini ({curr_p_str}) sudah berada tepat di bantalan support kuat. "
            f"Disarankan entry beli di target harga {entry_p_str}. "
            f"Selama harga bertahan di atas batas Cut Loss {cl_p_str}, potensi kenaikan menuju TP 1 {tp1_str}"
            f"{f' hingga TP 2 {fmt_price(best_tp2)}' if best_tp2 else ''} sangat menjanjikan dengan Risk/Reward {best_rr}x."
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
            "tp_list": tp_list,
            "cl": target_cl_clean
        }
    }
