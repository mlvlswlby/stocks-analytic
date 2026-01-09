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
import requests

try:
    from .analysis import calculate_technicals, detect_chart_patterns, generate_recommendation, calculate_forecast, calculate_seasonal
    from .tickers import STOCKS_DB
except ImportError:
    from analysis import calculate_technicals, detect_chart_patterns, generate_recommendation, calculate_forecast, calculate_seasonal
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

@app.get("/api/search")
@app.get("/api/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """
    Online Autocomplete search using Yahoo Finance API.
    """
    try:
        # Proxy to Yahoo Finance Autocomplete
        # Using query1 as it can be faster/less throttled sometimes
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        params = {
            "q": q,
            "quotesCount": 10,
            "newsCount": 0,
            "enableFuzzyQuery": "false",
            "quotesQueryId": "tss_match_phrase_query"
        }
        
        # Reduced timeout to 3s for snappier experience (or fail fast)
        resp = requests.get(url, params=params, headers=headers, timeout=3)
        data = resp.json()
        
        results = []
        if "quotes" in data:
            for quote in data["quotes"]:
                # Only interested in Equities/ETFs primarily, but let's take all to be safe
                if quote.get("quoteType", "") in ["EQUITY", "ETF", "MUTUALFUND", "INDEX", "FUTURE", "CURRENCY"]:
                    results.append({
                        "symbol": quote.get("symbol"),
                        "name": quote.get("longname") or quote.get("shortname") or quote.get("symbol"),
                        "exchange": quote.get("exchange", "")
                    })
        
        return clean_nans({"results": results})
        
    except Exception as e:
        print(f"Search API Error: {e}")
        # Fallback to local filtering if online fails
        return clean_nans({"results": []})

def get_stock_data(ticker: str, period="2y", interval="1d"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock data not found")
        
    return stock, df

@app.get("/api/stock/{ticker}")
def get_stock_details(ticker: str):
    print(f"DEBUG: Fetching details for {ticker}")
    # Optimize: Don't fetch history if we just need info.
    stock = yf.Ticker(ticker)
    
    try:
        info = stock.info
        print(f"DEBUG: Info fetched for {ticker}")
    except Exception as e:
        print(f"DEBUG: Info fetch failed for {ticker}: {e}")
        info = {}
        
    # Validating symbol via info usually works, but sometimes info is empty.
    # We can assume it exists if user searched it, or check fast_info.
    
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
        
    print(f"DEBUG: Returning details for {ticker}")
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
    print(f"DEBUG: Computing technicals for {ticker}")
    # Optimize: 1y is enough for SMA 200
    stock, df = get_stock_data(ticker, period="1y")
    print(f"DEBUG: Data fetched for technicals {ticker}, len={len(df)}")
    
    # Calculate indicators
    df = calculate_technicals(df)
    print("DEBUG: Indicators calculated")
    
    # Get patterns & recommendation
    chart_patterns = detect_chart_patterns(df)
    print(f"DEBUG: Patterns detected: {chart_patterns}")
    recommendation, score, reasons, trend_details = generate_recommendation(df)
    print(f"DEBUG: Recommendation generated: {recommendation}")
    
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
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        target_price = info.get("targetMeanPrice")
        if current_price and target_price:
            upside = (target_price - current_price) / current_price
            if upside > 0.20:
                 score += 5
                 reasons.append(f"Catalyst: Analyst Upside Potential ({(upside*100):.1f}%)")
                 
    except Exception as e:
        print(f"Fundamenal check failed: {e}")
    
    # Cap score
    score = max(0, min(100, score))

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
