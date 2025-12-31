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
    from .analysis import calculate_technicals, detect_candle_patterns, detect_chart_patterns, generate_recommendation
    from .tickers import STOCKS_DB
except ImportError:
    from analysis import calculate_technicals, detect_candle_patterns, detect_chart_patterns, generate_recommendation
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

@app.get("/api/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """
    Autocomplete search from local DB or passthrough.
    """
    q_upper = q.upper()
    results = [s for s in STOCKS_DB if q_upper in s["symbol"] or q_upper in s["name"].upper()]
    
    # If no local results, add the query itself as a fallback option
    if not results:
        results.append({"symbol": q_upper, "name": q_upper})
        
    return clean_nans({"results": results[:5]})

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
    return clean_nans({
        "symbol": ticker,
        "name": info.get("longName", ticker),
        "price": info.get("currentPrice", info.get("previousClose")),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "description": info.get("longBusinessSummary", "N/A"),
    })

@app.get("/api/stock/{ticker}/technicals")
def get_technicals(ticker: str):
    # Optimize: 1y is enough for SMA 200
    stock, df = get_stock_data(ticker, period="1y")
    
    # Calculate indicators
    df = calculate_technicals(df)
    
    # Get patterns & recommendation
    candle_patterns = detect_candle_patterns(df)
    chart_patterns = detect_chart_patterns(df)
    recommendation, score, reasons, trend_details = generate_recommendation(df)
    
    last = df.iloc[-1]
    
    return clean_nans({
        "symbol": ticker,
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
            "chart": chart_patterns
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
            # Fetch last 8 quarters (2 years)
            for date in income_stmt.columns[:8]:
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
