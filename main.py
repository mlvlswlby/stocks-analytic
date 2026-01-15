from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
import json
import math
import os

try:
    from .analysis import calculate_technicals, detect_candle_patterns, determine_market_trend, generate_recommendation, calculate_forecast, calculate_seasonal, generate_trade_plan
    from .tickers import STOCKS_DB
except ImportError:
    from analysis import calculate_technicals, detect_candle_patterns, determine_market_trend, generate_recommendation, calculate_forecast, calculate_seasonal, generate_trade_plan
    from tickers import STOCKS_DB

# Utility to clean NaNs for JSON compliance
def clean_nans(obj):
    if isinstance(obj, float):
        return None if math.isnan(obj) or math.isinf(obj) else obj
    elif isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(v) for v in obj]
    return obj

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Determine path to static files
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")

# Check if static dir exists there, if not try 'backend/static' (local run from root)
if not os.path.exists(static_dir):
    static_dir = os.path.join(current_dir, "../backend/static")
    if not os.path.exists(static_dir):
        static_dir = "backend/static"

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.get("/favicon.ico")
async def favicon():
    # Return 404 cleanly or a dummy file. 
    # For now, just raising 404 is fine but user complained about log.
    # Return empty content or 204 No Content to silence it?
    # Or just ignore. The LOG is the issue. 
    # Let's return a 204 No Content.
    from fastapi import Response
    return Response(status_code=204)

import requests

@app.get("/api/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """
    Autocomplete search using Yahoo Finance API.
    """
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        params = {
            'q': q,
            'quotesCount': 20,
            'newsCount': 0,
            'enableFuzzyQuery': 'false',
            'quotesQueryId': 'tss_match_phrase_query'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        
        results = []
        if 'quotes' in data:
            for item in data['quotes']:
                # Filter for equity/etf kind of things generally, or just return everything useful
                if 'symbol' in item:
                    # Normalize Exchange Label
                    symbol = item['symbol']
                    exch = item.get('exchange', '').upper()
                    
                    if symbol.endswith('.JK') or exch == 'JKT':
                        display_exchange = 'IDX'
                    elif 'NASDAQ' in exch or exch in ['NMS', 'NGM']:
                        display_exchange = 'NDX'
                    elif exch in ['NYQ', 'NYSE']:
                        display_exchange = 'NYSE'
                    else:
                        display_exchange = exch or 'EQ'

                    results.append({
                        "symbol": symbol,
                        "name": item.get('longname') or item.get('shortname') or item.get('name', 'N/A'),
                        "exchange": display_exchange
                    })
        
        return clean_nans({"results": results})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        # Fallback to empty list or basic echo if API fails
        return clean_nans({"results": []})

@app.get("/api/market-summary")
def get_market_summary():
    """
    Get real-time data for Top 10 IDX and Nasdaq stocks for ticker tapes.
    """
    # Fixed Top Market Cap Lists
    idx_tickers = ['BBCA.JK', 'BBRI.JK', 'BMRI.JK', 'BBNI.JK', 'TLKM.JK', 'ASII.JK', 'UNVR.JK', 'ICBP.JK', 'GOTO.JK', 'ADRO.JK']
    nasdaq_tickers = ['NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'META', 'TSLA', 'AMD', 'NFLX', 'INTC']
    
    try:
        all_tickers = idx_tickers + nasdaq_tickers
        # Download last 5 days to ensure we have previous close (handling weekends)
        df = yf.download(all_tickers, period="5d", progress=False)
        
        # yfinance returns MultiIndex columns: (Price, Ticker)
        # We want 'Close'
        close_df = df['Close']
        
        batch_results = {"idx": [], "nasdaq": []}
        
        for t in all_tickers:
            try:
                if t not in close_df:
                    continue
                    
                series = close_df[t].dropna()
                if len(series) >= 2:
                    current = series.iloc[-1]
                    prev = series.iloc[-2]
                    change = current - prev
                    pchange = (change / prev) * 100
                    
                    item = {
                        "symbol": t,
                        "price": float(current), # Ensure explicit float for JSON
                        "change": float(change),
                        "pchange": float(pchange)
                    }
                    
                    if t in idx_tickers:
                        batch_results["idx"].append(item)
                    else:
                        batch_results["nasdaq"].append(item)
            except Exception:
                continue
                
        return clean_nans(batch_results)

    except Exception as e:
        print(f"Market Summary Error: {e}")
        return {"idx": [], "nasdaq": []}

def get_stock_data(ticker: str, period="2y", interval="1d"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock data not found")
        
    return stock, df

@app.get("/api/stock/{ticker}")
def get_stock_details(ticker: str):
    stock, df = get_stock_data(ticker, period="1d")
    info = stock.info
    # Try to find logo - use Clearbit API as reliable fallback if website exists
    # Try to find logo - use Clearbit API as reliable fallback
    website = info.get("website")
    logo_url = info.get("logo_url", "")
    
    if not logo_url and website:
        try:
            # Clean url
            clean_url = website.lower().replace("https://", "").replace("http://", "").split("/")[0]
            
            # Remove common subdomains that might break logo lookup (ir., investors., www.)
            # This is a heuristic. Ideally usage of tldextract is better but avoiding extra deps.
            parts = clean_url.split('.')
            if len(parts) > 2:
                # likely subdomain.domain.com. Keep last two.
                # Exception: co.uk, com.sg etc. But for US stocks (most common) last 2 is safe.
                # Let's try to strip specifically known subdomains first
                for sub in ["www.", "ir.", "investors.", "investor.", "corporate."]:
                    if clean_url.startswith(sub):
                        clean_url = clean_url.replace(sub, "")
                        break
            
            logo_url = f"https://logo.clearbit.com/{clean_url}"
        except Exception:
            logo_url = ""
        
        
    return clean_nans({
        "symbol": ticker,
        "name": info.get("longName", ticker),
        "price": info.get("currentPrice", info.get("previousClose")),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "description": info.get("longBusinessSummary", "N/A"),
        "logo_url": logo_url,
        "domain": website.replace("https://", "").replace("http://", "").split("/")[0] if website else ""
    })

@app.get("/api/stock/{ticker}/technicals")
def get_technicals(ticker: str):
    # Optimize: 1y is enough for SMA 200
    stock, df = get_stock_data(ticker, period="1y")
    
    # Calculate indicators
    df = calculate_technicals(df)
    
    # Get patterns & recommendation
    candle_patterns = detect_candle_patterns(df)
    market_trend = determine_market_trend(df)
    recommendation, score, reasons, trend_details = generate_recommendation(df)
    
    # --- Fundamental Analysis / Catalyst Injection ---
    # We fetch info again or reuse if possible. get_stock_details fetches it but we are in get_technicals.
    # We already have 'stock' object.
    try:
        info = stock.info
        
        # P/E Ratio
        pe = info.get("trailingPE") or info.get("forwardPE")
        if pe:
            if pe < 15:
                score += 5
                reasons.append(f"Fundamental: Undervalued (P/E {pe:.1f} < 15)")
            elif pe > 50:
                score -= 5
                reasons.append(f"Fundamental: Overvalued (P/E {pe:.1f} > 50)")

        # Market Cap (Small Cap vs Large Cap) - Minimal impact but useful context
        mcap = info.get("marketCap")
        if mcap and mcap > 100_000_000_000: # 100B
            score += 2 # Slight bias for stability
        
        # Revenue Growth
        rev_growth = info.get("revenueGrowth")
        if rev_growth and rev_growth > 0.20:
             score += 5
             reasons.append(f"Catalyst: High Revenue Growth ({(rev_growth*100):.1f}%)")
             
        # Margins
        profit_margin = info.get("profitMargins")
        if profit_margin and profit_margin > 0.20:
            reasons.append(f"Fundamental: High Profit Margin ({(profit_margin*100):.1f}%)")
            
        # Analyst Target
        current_price_info = info.get("currentPrice") or info.get("regularMarketPrice")
        target_price = info.get("targetMeanPrice")
        if current_price_info and target_price:
            upside = (target_price - current_price_info) / current_price_info
            if upside > 0.20:
                 score += 5
                 reasons.append(f"Catalyst: Analyst Upside Potential ({(upside*100):.1f}%)")
                 
    except Exception as e:
        # Pass silently or log
        pass

    # Cap score
    score = max(0, min(100, score))

    last = df.iloc[-1]
    
    return clean_nans({
        "symbol": ticker,
        "current_price": float(last['Close']),
        "sma_50": float(last['SMA_50']),
        "sma_200": float(last['SMA_200']),
        "rsi": float(last['RSI']),
        "recommendation": recommendation,
        "score": score,
        "reasons": reasons,
        "trend_details": trend_details,
        "indicators": {
            "SMA_10": last.get("SMA_10"),
            "SMA_20": last.get("SMA_20"),
            "SMA_50": last.get("SMA_50"),
            "SMA_100": last.get("SMA_100"),
            "SMA_200": last.get("SMA_200"),
            "RSI": last.get("RSI"),
            "Stochastic_K": last.get("K"),
            "Stochastic_D": last.get("D"),
        },
        "patterns": {
            "candle": candle_patterns,
            "trend": market_trend
        }
    })

@app.get("/api/stock/{ticker}/fundamentals")
def get_fundamentals(ticker: str):
    stock, _ = get_stock_data(ticker)
    info = stock.info
    
    # Financials (Quarterly)
    financials_data = []
    try:
        income_stmt = stock.quarterly_income_stmt
        
        if not income_stmt.empty:
            # Fetch last 12 quarters (3 years)
            for date in income_stmt.columns[:12]:
                col = income_stmt[date]
                try:
                    # Robust key search
                    revenue = col.get("Total Revenue") or col.get("TotalRevenue") or 0
                    net_inc = col.get("Net Income") or col.get("NetIncome") or 0
                    op_exp = col.get("Operating Expense") or col.get("OperatingExpense") or col.get("Operating Expenses") or 0
                    
                    fin_obj = {
                        "date": str(date.date()) if hasattr(date, 'date') else str(date),
                        "revenue": revenue,
                        "net_income": net_inc,
                        "operating_expense": op_exp,
                    }
                    financials_data.append(fin_obj)
                except Exception:
                    continue
    except Exception as e:
        print(f"Error fetching fundamentals: {e}")
            
    return clean_nans({
        "symbol": ticker,
        "ratios": {
            "PER": info.get("trailingPE") or info.get("forwardPE"),
            "PBV": info.get("priceToBook"),
            "MarketCap": info.get("marketCap"),
        },
        "financials": financials_data
    })

@app.get("/api/stock/{ticker}/forecast")
def get_forecast_data(ticker: str):
    stock, df = get_stock_data(ticker, period="2y") # Need enough history for trend
    forecast = calculate_forecast(df)
    return clean_nans(forecast)

@app.get("/api/stock/{ticker}/seasonal")
def get_seasonal_data(ticker: str):
    stock, df = get_stock_data(ticker, period="5y") # Need years of history
    seasonal = calculate_seasonal(df)
    return clean_nans(seasonal)

@app.get("/api/stock/{ticker}/chart")
def get_chart_data(ticker: str, range: str = "1y"):
    allowed_ranges = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
    period = allowed_ranges.get(range, "1y")
    
    stock, df = get_stock_data(ticker, period=period)
    
    # Format for chart
    chart_data = []
    for index, row in df.iterrows():
        chart_data.append({
            "time": str(index.date()),
            "open": row["Open"],
            "high": row["High"],
            "low": row["Low"],
            "close": row["Close"],
            "volume": row["Volume"]
        })
        
    return clean_nans(chart_data)

@app.get("/api/analyze-trade")
def analyze_trade(ticker: str, avg_price: float, start_date: str = None):
    # Fetch ample history for analysis
    # We use '2y' to ensure enough data for SMA200 and support/resistance
    stock, df = get_stock_data(ticker, period="2y") 
    df = calculate_technicals(df) # Ensure indicators are present
    
    plan = generate_trade_plan(df, avg_price, start_date)
    return clean_nans(plan)
