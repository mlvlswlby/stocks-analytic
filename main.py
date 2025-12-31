
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import json
from .analysis import calculate_technicals, detect_candle_patterns, detect_chart_patterns, generate_recommendation

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Enable CORS for frontend (useful if running separately, but we serve static now)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="backend/static"), name="static")

@app.get("/")
def read_root():
    return FileResponse('backend/static/index.html')

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
            "Stochastic_K": last.get("STOCHk_14_3_3"),
            "Stochastic_D": last.get("STOCHd_14_3_3"),
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
    # yfinance often returns DataFrame for financials
    income_stmt = stock.quarterly_income_stmt
    balance_sheet = stock.quarterly_balance_sheet
    
    # Extract last 4 quarters if available
    financials_data = []
    if not income_stmt.empty:
        # formatting...
        for date in income_stmt.columns[:4]: # last 4 quarters
            col = income_stmt[date]
            fin_obj = {
                "date": str(date.date()),
                "revenue": col.get("Total Revenue", col.get("TotalRevenue", 0)),
                "net_income": col.get("Net Income", col.get("NetIncome", 0)),
                "operating_expense": col.get("Operating Expense", col.get("OperatingExpense", 0)), # keys vary by yf version
            }
            financials_data.append(fin_obj)
            
    return {
        "symbol": ticker,
        "ratios": {
            "PER": info.get("trailingPE"),
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
