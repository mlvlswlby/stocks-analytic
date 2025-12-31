
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import json
try:
    from .analysis import calculate_technicals, detect_candle_patterns, detect_chart_patterns, generate_recommendation
except ImportError:
    from analysis import calculate_technicals, detect_candle_patterns, detect_chart_patterns, generate_recommendation

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import os

app = FastAPI()

# Enable CORS for frontend (useful if running separately, but we serve static now)
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
    static_dir = os.path.join(current_dir, "../backend/static") # If running from root, main is in backend module
    if not os.path.exists(static_dir):
        static_dir = "backend/static" # Fallback

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.get("/api/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """
    Search for stocks.
    For IDX stocks, user might type 'BBCA', we might need to append '.JK' if not present,
    but yfinance usually handles standard tickers.
    """
    try:
        # yfinance search is a bit limited programmatically without extra libraries,
        # but we can try to fetch info or use a predefined list later.
        # For now, we will return the query as a ticker candidate if it looks valid.
        # Ideally, we would use a proper search API.
        
        # Simple passthrough for valid-looking tickers
        return {"results": [{"symbol": q.upper(), "name": q.upper()}]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_stock_data(ticker: str, period="2y", interval="1d"):
    if not ticker.endswith(".JK") and not ticker.isalpha(): 
        # Heuristic: if it's not .JK and strictly letters, it might be US.
        # If user explicitly asks for indonesia, they should probably suffix .JK or we handle it in frontend.
        pass
        
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock data not found")
        
    return stock, df

@app.get("/api/stock/{ticker}")
def get_stock_details(ticker: str):
    stock, df = get_stock_data(ticker, period="1d") # just need info
    info = stock.info
    return {
        "symbol": ticker,
        "name": info.get("longName", ticker),
        "price": info.get("currentPrice", info.get("previousClose")),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "description": info.get("longBusinessSummary", "N/A"),
    }

@app.get("/api/stock/{ticker}/technicals")
def get_technicals(ticker: str):
    stock, df = get_stock_data(ticker, period="3y") # Need enough data for SMA200
    
    # Calculate indicators
    df = calculate_technicals(df)
    
    # Get patterns & recommendation
    candle_patterns = detect_candle_patterns(df)
    chart_patterns = detect_chart_patterns(df)
    recommendation, score = generate_recommendation(df)
    
    last = df.iloc[-1]
    
    return {
        "symbol": ticker,
        "recommendation": recommendation,
        "score": score,
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
    }

@app.get("/api/stock/{ticker}/fundamentals")
def get_fundamentals(ticker: str):
    stock, _ = get_stock_data(ticker)
    info = stock.info
    
    # Financials (Quarterly)
    financials_data = []
    try:
        income_stmt = stock.quarterly_income_stmt
        
        if not income_stmt.empty:
            for date in income_stmt.columns[:4]: # last 4 quarters
                col = income_stmt[date]
                try:
                    # Robust key search for "Total Revenue"
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
            
    return {
        "symbol": ticker,
        "ratios": {
            "PER": info.get("trailingPE") or info.get("forwardPE"),
            "PBV": info.get("priceToBook"),
            "MarketCap": info.get("marketCap"),
        },
        "financials": financials_data
    }

@app.get("/api/stock/{ticker}/chart")
def get_chart_data(ticker: str, range: str = "1y"):
    allowed_ranges = {"1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
    period = allowed_ranges.get(range, "1y")
    
    stock, df = get_stock_data(ticker, period=period)
    
    # Format for chart (e.g. lightweight-charts expects: time, open, high, low, close)
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
        
    return chart_data
