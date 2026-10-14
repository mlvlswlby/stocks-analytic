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
import asyncio

try:
    from .analysis import calculate_technicals, detect_candle_patterns, determine_market_trend, generate_recommendation, calculate_forecast, calculate_seasonal, generate_trade_plan, generate_entry_plan
    from .tickers import STOCKS_DB
except ImportError:
    from analysis import calculate_technicals, detect_candle_patterns, determine_market_trend, generate_recommendation, calculate_forecast, calculate_seasonal, generate_trade_plan, generate_entry_plan
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

from starlette.middleware.cors import CORSMiddleware as _CORSMiddleware
from starlette.types import ASGIApp

class CustomCORSMiddleware(_CORSMiddleware):
    def __init__(self, app: ASGIApp, *args, **kwargs):
        super().__init__(app, *args, **kwargs)
        self.simple_headers["Access-Control-Allow-Private-Network"] = "true"
        self.preflight_headers["Access-Control-Allow-Private-Network"] = "true"
        if "Vary" in self.preflight_headers:
            self.preflight_headers["Vary"] += ", Access-Control-Request-Private-Network"
        else:
            self.preflight_headers["Vary"] = "Origin, Access-Control-Request-Private-Network"

app = FastAPI()

# Enable CORS with Private Network Access
app.add_middleware(
    CustomCORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# Determine path to static files (frontend folder)
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "../frontend")

if not os.path.exists(static_dir):
    static_dir = "frontend"

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        response = FileResponse(index_path)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response
    return {"message": "Frontend not found. API is running."}

@app.get("/debug-paths")
def debug_paths():
    import os
    items = []
    if os.path.exists(static_dir):
        items = os.listdir(static_dir)
    return {
        "cwd": os.getcwd(),
        "__file__": __file__,
        "static_dir": static_dir,
        "exists": os.path.exists(static_dir),
        "items": items,
        "env_port": os.getenv("PORT")
    }

@app.get("/favicon.ico")
async def favicon():
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

TOP_20_CACHE = {"idx": [], "nasdaq": []}

async def update_top_20_loop():
    while True:
        try:
            print("Background Update: Evaluating Top 20 Buy Recommendations...")
            idx_symbols = [s["symbol"] for s in STOCKS_DB if s["symbol"].endswith('.JK') or s.get("exchange", "").upper() in ['JKT', 'IDX']]
            us_symbols = [s["symbol"] for s in STOCKS_DB if not s["symbol"].endswith('.JK') and s.get("exchange", "").upper() not in ['JKT', 'IDX']]
            
            all_idx = []
            all_us = []
            
            for symbol in [s["symbol"] for s in STOCKS_DB]:
                try:
                    stock = yf.Ticker(symbol)
                    # Run synchronous network request in a separate thread so we don't block FastAPI
                    df_ticker = await asyncio.to_thread(stock.history, period="1y")
                    
                    if df_ticker.empty or len(df_ticker) < 50:
                        continue
                        
                    # Calculate Technicals & Recommendation
                    df_tech = calculate_technicals(df_ticker)
                    recommendation, score, _, _ = generate_recommendation(df_tech)
                    
                    current = df_tech.iloc[-1]
                    prev = df_tech.iloc[-2]
                    change = current["Close"] - prev["Close"]
                    pchange = (change / prev["Close"]) * 100
                    
                    # We still evaluate technicals but the ticker tape priority is now Top Gainer %
                    # You requested top 20 gainer movement
                    
                    item = {
                        "symbol": symbol,
                        "price": float(current["Close"]),
                        "change": float(change),
                        "pchange": float(pchange),
                        "score": score
                    }
                    
                    if symbol in idx_symbols:
                        all_idx.append(item)
                    else:
                        all_us.append(item)
                except Exception as e:
                    # Suppress individual stock errors to keep sweeping
                    pass
                    
            # Sort strictly by Percentage Change (Top Gainers) descending
            all_idx.sort(key=lambda x: x["pchange"], reverse=True)
            all_us.sort(key=lambda x: x["pchange"], reverse=True)
            
            def get_top_gainers_losers(data):
                if len(data) <= 20:
                    return data
                gainers = data[:10] # Top 10 gainers (highest positive)
                losers = sorted(data[-10:], key=lambda x: x["pchange"]) # Top 10 losers (lowest negative)
                return gainers + losers
            
            TOP_20_CACHE["idx"] = get_top_gainers_losers(all_idx)
            TOP_20_CACHE["nasdaq"] = get_top_gainers_losers(all_us)
            print(f"Background Update Complete! IDX: {len(TOP_20_CACHE['idx'])}, US: {len(TOP_20_CACHE['nasdaq'])}")
            
        except Exception as e:
            print(f"Error in background evaluation loop: {e}")
            
        # Refresh every hour
        await asyncio.sleep(3600)

@app.on_event("startup")
async def startup_event():
    # Initial fallback so cache isn't entirely empty during the first cycle (padded to 20 to preserve ticker speed)
    TOP_20_CACHE["idx"] = [
        {"symbol": "MEMUAT..", "price": 0.0, "change": 0.0, "pchange": 0.0, "score": 0}
    ] * 20
    TOP_20_CACHE["nasdaq"] = [
        {"symbol": "LOADING..", "price": 0.0, "change": 0.0, "pchange": 0.0, "score": 0}
    ] * 20
    asyncio.create_task(update_top_20_loop())

@app.get("/api/market-summary")
def get_market_summary():
    """
    Get cached dynamically evaluated Top 20 Buy recommendations.
    """
    return clean_nans(TOP_20_CACHE)

def get_stock_data(ticker: str, period="2y", interval="1d"):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="Stock data not found")
        
    return stock, df

# Curated profiles for primary IDX stocks to guarantee rich Indonesian descriptions
KNOWN_PROFILES = {
    "BBCA.JK": {
        "name": "PT Bank Central Asia Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "description": "PT Bank Central Asia Tbk (BCA) adalah bank swasta terbesar di Indonesia yang menyediakan beragam solusi perbankan dan keuangan terpadu bagi nasabah perorangan, usaha kecil dan menengah (UKM), serta korporasi.",
        "website": "https://www.bca.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Bank_Central_Asia.svg/330px-Bank_Central_Asia.svg.png"
    },
    "BBRI.JK": {
        "name": "PT Bank Rakyat Indonesia (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "description": "PT Bank Rakyat Indonesia (Persero) Tbk (BRI) adalah salah satu bank milik negara terbesar di Indonesia yang memiliki spesialisasi dan fokus utama pada pemberdayaan segmen usaha mikro, kecil, dan menengah (UMKM).",
        "website": "https://www.bri.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9a/BRI_2025_%28with_full_name%29.svg/330px-BRI_2025_%28with_full_name%29.svg.png"
    },
    "BMRI.JK": {
        "name": "PT Bank Mandiri (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "description": "PT Bank Mandiri (Persero) Tbk adalah salah satu bank BUMN terbesar di Indonesia dengan portofolio pembiayaan korporasi, komersial, ritel, dan digital banking (Livin' & Kopra) yang sangat kuat.",
        "website": "https://www.bankmandiri.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Bank_Mandiri_logo_2016.svg/330px-Bank_Mandiri_logo_2016.svg.png"
    },
    "BBNI.JK": {
        "name": "PT Bank Negara Indonesia (Persero) Tbk",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "description": "PT Bank Negara Indonesia (Persero) Tbk (BNI) adalah salah satu institusi perbankan tertua di Indonesia yang memiliki fokus kuat pada pembiayaan korporasi, konsumer, dan jaringan operasional internasional.",
        "website": "https://www.bni.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/5/5a/Bank_Negara_Indonesia_logo.svg/330px-Bank_Negara_Indonesia_logo.svg.png"
    },
    "TLKM.JK": {
        "name": "PT Telkom Indonesia (Persero) Tbk",
        "sector": "Communication Services",
        "industry": "Telecom Services",
        "description": "PT Telkom Indonesia (Persero) Tbk adalah BUMN telekomunikasi dan jaringan digital terbesar di Indonesia, melayani ratusan juta pelanggan seluler (Telkomsel) serta internet fixed broadband (IndiHome).",
        "website": "https://www.telkom.co.id",
        "logo_url": "https://thumb.wikimedia.org/wikipedia/id/thumb/c/c4/Telkom_Indonesia_2013.svg/langid-330px-Telkom_Indonesia_2013.svg.png"
    },
    "ASII.JK": {
        "name": "PT Astra International Tbk",
        "sector": "Consumer Cyclical",
        "industry": "Auto Manufacturers",
        "description": "PT Astra International Tbk adalah salah satu konglomerasi terbesar di Indonesia dengan lini bisnis otomotif, jasa keuangan, alat berat & pertambangan (United Tractors), agribisnis, dan infrastruktur.",
        "website": "https://www.astra.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Astra_International_logo.svg/330px-Astra_International_logo.svg.png"
    },
    "UNVR.JK": {
        "name": "PT Unilever Indonesia Tbk",
        "sector": "Consumer Defensive",
        "industry": "Household & Personal Products",
        "description": "PT Unilever Indonesia Tbk adalah produsen barang kebutuhan konsumen sehari-hari (FMCG) terkemuka di Indonesia yang memproduksi makanan, minuman, produk pembersih rumah tangga, dan perawatan tubuh.",
        "website": "https://www.unilever.co.id",
        "logo_url": "https://upload.wikimedia.org/wikipedia/en/thumb/e/e4/Unilever.svg/330px-Unilever.svg.png"
    },
    "GOTO.JK": {
        "name": "PT GoTo Gojek Tokopedia Tbk",
        "sector": "Technology",
        "industry": "Internet Content & Information",
        "description": "PT GoTo Gojek Tokopedia Tbk adalah ekosistem digital terbesar di Indonesia yang menggabungkan layanan on-demand (Gojek), e-commerce (Tokopedia), dan layanan teknologi finansial terintegrasi (GoPay).",
        "website": "https://www.gotocompany.com",
        "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/30/GoTo_logo.svg/330px-GoTo_logo.svg.png"
    },
    "ICBP.JK": {
        "name": "PT Indofood CBP Sukses Makmur Tbk",
        "sector": "Consumer Defensive",
        "industry": "Packaged Foods",
        "description": "PT Indofood CBP Sukses Makmur Tbk adalah produsen makanan olahan dalam kemasan terkemuka di Indonesia dengan merek legendaris seperti mi instan Indomie, susu Indomilk, dan aneka bumbu makanan.",
        "website": "https://www.indofoodcbp.com"
    },
    "INDF.JK": {
        "name": "PT Indofood Sukses Makmur Tbk",
        "sector": "Consumer Defensive",
        "industry": "Packaged Foods",
        "description": "PT Indofood Sukses Makmur Tbk adalah perusahaan total food solutions terkemuka di Indonesia dengan operasi bisnis yang mencakup seluruh tahapan proses produksi makanan dari perkebunan hingga ritel.",
        "website": "https://www.indofood.com"
    },
    "ADRO.JK": {
        "name": "PT Adaro Energy Indonesia Tbk",
        "sector": "Energy",
        "industry": "Thermal Coal",
        "description": "PT Adaro Energy Indonesia Tbk adalah grup energi dan pertambangan batu bara terintegrasi di Indonesia yang kini aktif mengembangkan pilar bisnis energi hijau, pembangkit listrik, dan smelter aluminium.",
        "website": "https://www.adaro.com"
    },
    "PTBA.JK": {
        "name": "PT Bukit Asam Tbk",
        "sector": "Energy",
        "industry": "Thermal Coal",
        "description": "PT Bukit Asam Tbk adalah anggota holding industri pertambangan BUMN (MIND ID) yang bergerak di bidang pertambangan batu bara terintegrasi dan ketenagalistrikan nasional.",
        "website": "https://www.ptba.co.id"
    },
    "ANTM.JK": {
        "name": "PT Aneka Tambang Tbk",
        "sector": "Basic Materials",
        "industry": "Other Industrial Metals & Mining",
        "description": "PT Aneka Tambang Tbk (Antam) adalah anggota MIND ID yang bergerak di bidang eksplorasi, penambangan, pengolahan serta pemurnian komoditas emas mulia, feronikel, dan bauksit.",
        "website": "https://www.antam.com"
    },
    "PGAS.JK": {
        "name": "PT Perusahaan Gas Negara Tbk",
        "sector": "Utilities",
        "industry": "Utilities - Regulated Gas",
        "description": "PT Perusahaan Gas Negara Tbk (PGN) adalah subholding gas Pertamina yang mengelola jaringan transmisi dan distribusi gas bumi terbesar di Indonesia untuk kebutuhan industri dan rumah tangga.",
        "website": "https://www.pgn.co.id"
    }
}

def resolve_company_profile(ticker: str, stock, df: pd.DataFrame) -> dict:
    ticker_upper = ticker.upper()
    known = KNOWN_PROFILES.get(ticker_upper, {})
    
    # Try fetching stock.info safely
    info = {}
    try:
        info = stock.info or {}
    except Exception:
        info = {}
        
    # Get reliable closing price from dataframe
    last_price = float(df.iloc[-1]['Close']) if not df.empty else (info.get("currentPrice") or info.get("previousClose") or 0.0)
    
    name = info.get("longName") or info.get("shortName") or known.get("name")
    sector = info.get("sector") or known.get("sector")
    industry = info.get("industry") or known.get("industry")
    description = info.get("longBusinessSummary") or known.get("description")
    website = info.get("website") or known.get("website") or ""
    logo_url = info.get("logo_url") or known.get("logo_url") or ""
    
    # If sector, industry, or name is missing, query Yahoo Search API (public, no crumb needed)
    if not sector or sector == "N/A" or not industry or industry == "N/A" or not name or name == ticker_upper:
        try:
            url = "https://query2.finance.yahoo.com/v1/finance/search"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            resp = requests.get(url, headers=headers, params={"q": ticker_upper, "quotesCount": 1}, timeout=3)
            if resp.ok:
                data = resp.json()
                quotes = data.get("quotes", [])
                if quotes:
                    q = quotes[0]
                    name = name or q.get("longname") or q.get("shortname")
                    sector = sector or q.get("sectorDisp") or q.get("sector")
                    industry = industry or q.get("industryDisp") or q.get("industry")
        except Exception as e:
            print(f"Yahoo Search profile error: {e}")

    # If description is still missing, query Wikipedia REST API (fast & free)
    if not description or description == "N/A" or len(description) < 15:
        try:
            clean_name = (name or ticker_upper)
            for stopword in ["(Persero)", "PT ", "PT. ", " Tbk", " Tbk.", " Corp.", " Corporation", " Inc.", " Co., Ltd.", " Ltd."]:
                clean_name = clean_name.replace(stopword, "")
            clean_name = clean_name.strip().replace(" ", "_")
            
            headers = {'User-Agent': 'StocksAnalyticApp/1.0 (info@stocks-analytic.local)'}
            wiki_langs = ["id", "en"] if ticker_upper.endswith(".JK") else ["en", "id"]
            for lang in wiki_langs:
                wiki_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{clean_name}"
                w_resp = requests.get(wiki_url, headers=headers, timeout=3)
                if w_resp.ok:
                    w_data = w_resp.json()
                    extract = w_data.get("extract")
                    if extract and len(extract) > 20:
                        description = extract
                        if not logo_url and w_data.get("thumbnail"):
                            logo_url = w_data["thumbnail"].get("source", "")
                        break
        except Exception as e:
            print(f"Wikipedia profile error: {e}")
            
    # Final fallbacks to ensure N/A NEVER appears
    name = name or ticker_upper
    sector = sector if sector and sector != "N/A" else ("Jasa Keuangan & Perbankan" if "BANK" in name.upper() else "Industri & Bisnis")
    industry = industry if industry and industry != "N/A" else ("Perbankan Komersial" if "BANK" in name.upper() else "Operasional Publik")
    
    if not description or description == "N/A" or len(description) < 15:
        exch_label = "Bursa Efek Indonesia (IDX)" if ticker_upper.endswith(".JK") else "Pasar Modal Global (US Market)"
        description = f"{name} ({ticker_upper}) adalah perusahaan terbuka yang sahamnya diperdagangkan di {exch_label}. Perusahaan bergerak di sektor {sector} dengan fokus kegiatan operasional pada {industry}."
        
    # Clearbit logo fallback if domain exists
    if not logo_url and website:
        try:
            clean_url = website.lower().replace("https://", "").replace("http://", "").split("/")[0]
            logo_url = f"https://logo.clearbit.com/{clean_url}"
        except Exception:
            logo_url = ""

    domain = website.replace("https://", "").replace("http://", "").split("/")[0] if website else ""

    return {
        "symbol": ticker_upper,
        "name": name,
        "price": last_price,
        "sector": sector,
        "industry": industry,
        "description": description,
        "logo_url": logo_url,
        "website": website,
        "domain": domain
    }

@app.get("/api/stock/{ticker}")
def get_stock_details(ticker: str):
    stock, df = get_stock_data(ticker, period="1d")
    profile = resolve_company_profile(ticker, stock, df)
    return clean_nans(profile)

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
    
    try:
        info = stock.info
    except Exception as e:
        print(f"yfinance info error: {e}")
        info = {}
    
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

@app.get("/api/stock/{ticker}/entry-plan")
def get_entry_plan(ticker: str):
    try:
        stock, df = get_stock_data(ticker, period="2y") 
        df = calculate_technicals(df) 
        
        plan = generate_entry_plan(df)
        return clean_nans(plan)
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}
