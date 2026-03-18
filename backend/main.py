import os
import sys
import logging
import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import urllib.parse

# CRITICAL: Path fix for services import
# This must be at the very top before any local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yfinance as yf
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from services.forecaster import ForecastEngine
from services.valuation import ValuationService
from services.technical_analysis import TechnicalAnalysisService

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# HELPER: Find Frontend Dist
def find_frontend_dist():
    possible_paths = [
        os.path.join(project_root, "frontend", "dist"),
        os.path.join(current_dir, "..", "frontend", "dist"),
        "/opt/render/project/src/frontend/dist"
    ]
    for p in possible_paths:
        abs_p = os.path.abspath(p)
        if os.path.exists(abs_p):
            logger.info(f"FOUND FRONTEND DIST AT: {abs_p}")
            return abs_p
    return None

frontend_dist = find_frontend_dist()

def json_compatible(item):
    if isinstance(item, dict): return {k: json_compatible(v) for k, v in item.items()}
    elif isinstance(item, (list, tuple, set)): return [json_compatible(i) for i in item]
    elif isinstance(item, (np.int64, np.int32, np.int16)): return int(item)
    elif isinstance(item, (np.float64, np.float32, np.float16)):
        if np.isnan(item) or np.isinf(item): return None
        return float(item)
    elif isinstance(item, (np.bool_)): return bool(item)
    elif pd.isna(item): return None
    return item

def safe_float(value, decimals=2):
    try:
        if value is None or pd.isna(value) or np.isinf(value): return None
        return round(float(value), decimals)
    except: return None

async def get_stock_news(ticker, company_name):
    """Fetch latest news using Google News RSS feed asynchronously."""
    try:
        query = f"{company_name} {ticker} stock"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                return []
            xml_data = response.text
            
        root = ET.fromstring(xml_data)
        news_items = []
        
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else "#"
            
            # Google RSS often includes publisher in the title: "Title - Publisher"
            # And also has a <source> tag
            source_el = item.find('source')
            publisher = source_el.text if source_el is not None else "Market News"
            
            if " - " in title and publisher in title:
                title = title.rsplit(" - ", 1)[0]

            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            
            news_items.append({
                "title": title,
                "link": link,
                "publisher": publisher,
                "time": pub_date
            })
        return news_items
    except Exception as e:
        logger.error(f"News RSS fetch error: {e}")
        return []

@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FinAdvisor API is running"}

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        
        # Parallelize data fetching to reduce latency
        # 1. info and fast_info are blocking calls
        # 2. Valuation calculation can also be blocking
        # 3. News fetch is now async
        
        loop = asyncio.get_event_loop()
        
        # Fetch basic info first (essential for other calls)
        info = await loop.run_in_executor(None, lambda: stock.info or {})
        fast = stock.fast_info
        
        # Rigorous check for ticker existence
        if not info or (not info.get('quoteType') and not info.get('symbol') and not info.get('regularMarketPrice')):
            if not getattr(fast, 'last_price', None):
                 raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found or has no public data.")

        quote_type = info.get('quoteType', 'EQUITY')
        is_etf = quote_type == 'ETF'
        comp_name = info.get('longName', ticker)

        # Run multiple heavy operations in parallel
        val_service = ValuationService(ticker)
        
        tasks = [
            loop.run_in_executor(None, val_service.run_dcf_model),
            loop.run_in_executor(None, val_service.get_performance_history),
            get_stock_news(ticker, comp_name)
        ]
        
        # Add ETF specific or dividend specific tasks if needed
        dcf_res, perf, news_items = await asyncio.gather(*tasks)

        current_p = safe_float(getattr(fast, 'last_price', None)) or safe_float(info.get('currentPrice'))
        if current_p is None:
            h = await loop.run_in_executor(None, lambda: stock.history(period="1d"))
            if not h.empty: current_p = safe_float(h['Close'].iloc[-1])
        
        if current_p is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' price data unavailable.")

        # ETF Specific Data: Holdings
        holdings = []
        if is_etf:
            try:
                raw_holdings = info.get('topHoldings', [])
                for h in raw_holdings[:10]:
                    holdings.append({
                        "symbol": h.get('symbol'),
                        "name": h.get('holdingName'),
                        "pct": safe_float(h.get('holdingPercent', 0) * 100)
                    })
            except: pass

        # Valuation Results
        intrinsic = safe_float(dcf_res.get('intrinsic_price')) or current_p
        status = dcf_res.get('status', 'NEUTRAL')
        calculation = dcf_res.get('calculation', '')
        error = dcf_res.get('error')
        industry_pe = safe_float(dcf_res.get('industry_pe')) or 20.0

        # Dividend & Expense Ratio
        exp = info.get('netExpenseRatio') or info.get('annualReportExpenseRatio') or info.get('expenseRatio')
        if exp is None and is_etf:
            try:
                # funds_data can be slow, but we only do it if necessary
                fd = await loop.run_in_executor(None, lambda: stock.funds_data)
                if fd and not fd.fund_operations.empty:
                    exp = fd.fund_operations.loc['Annual Report Expense Ratio'].iloc[0]
            except: pass
        
        if exp and exp < 0.01: exp *= 100
        if exp is None: exp = 0.0
        
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or info.get('yield') or 0.0
        if 0 < div_yield < 0.2: div_yield *= 100
        if (not div_rate or div_rate == 0) and div_yield > 0: div_rate = (div_yield / 100) * current_p

        # Fallback news if Google fails
        if not news_items:
            try:
                raw_y_news = await loop.run_in_executor(None, lambda: stock.news or [])
                news_items = [{
                    "title": n.get('title', 'No Title'),
                    "link": n.get('link', '#'),
                    "publisher": n.get('publisher', 'Market News'),
                    "time": n.get('providerPublishTime', '')
                } for n in raw_y_news[:5]]
            except: pass
            
        if not news_items:
            news_items = [{"title": f"Latest updates for {ticker}", "link": f"https://finance.yahoo.com/quote/{ticker}/news", "publisher": "Yahoo Finance", "time": ""}]

        return json_compatible({
            "ticker": ticker,
            "type": quote_type,
            "industry": info.get('industry', 'Exchange Traded Fund'),
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
                "calculation": calculation, "error": error,
                "eps": safe_float(info.get('trailingEps')), "pe": safe_float(info.get('trailingPE')), 
                "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(div_rate), "div_yield": safe_float(div_yield),
                "beta": safe_float(info.get('beta')), "expense_ratio": safe_float(exp), "exchange": info.get('exchange')
            },
            "holdings": holdings,
            "averages": {"pe": industry_pe, "eps": 4.2, "div": 1.5, "risk": 1.1, "exp": 0.45, "mkt": 150000000000},
            "performance": perf,
            "info": {"name": comp_name, "summary": info.get('longBusinessSummary', '')},
            "news": news_items
        })
    except HTTPException: raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk"), indicators: str = Query(None)):
    try:
        stock = yf.Ticker(ticker.upper())
        interval = "1d"
        if period == "1d": interval = "1h"
        elif period in ["5d", "1wk"]: interval = "1h"
        
        # Determine fetch period: If indicators are requested, we need more history for calculation
        fetch_period = period
        if indicators and period != "5y":
            if period in ["1d", "5d", "1wk", "1mo", "3mo", "ytd", "1y"]:
                fetch_period = "2y" # Fetch 2 years to be safe for all windows

        loop = asyncio.get_event_loop()
        hist = await loop.run_in_executor(None, lambda: stock.history(period=fetch_period, interval=interval).reset_index())
        
        if hist.empty: return {"data": []}
        
        # Apply Technical Indicators
        if indicators:
            ta_service = TechnicalAnalysisService(ticker)
            indicator_list = indicators.split(',')
            hist = await loop.run_in_executor(None, ta_service.calculate_indicators, hist, indicator_list)
            
            # Slice back to the requested period
            orig_hist = await loop.run_in_executor(None, lambda: stock.history(period=period, interval=interval))
            if not orig_hist.empty:
                start_date = orig_hist.index[0]
                hist = hist[hist['Date' if 'Date' in hist.columns else 'Datetime'] >= start_date]

        col = 'Date' if 'Date' in hist.columns else 'Datetime'
        if period == "1d":
            hist['date'] = hist[col].dt.strftime('%H:%M')
        else:
            hist['date'] = hist[col].dt.strftime('%m-%d %H:%M')
            
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        
        # Data columns to return
        return_cols = ['date', 'Close']
        if indicators:
            for ind in ['sma20', 'sma50', 'bb_upper', 'bb_lower', 'rsi', 'macd', 'macd_signal', 'macd_hist']:
                if ind in hist.columns: return_cols.append(ind)

        return json_compatible({
            "data": hist[return_cols].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": 0, "high": 0}, "resistance": {"low": 0, "high": 0}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
        })
    except Exception as e:
        logger.error(f"History error: {e}")
        return {"data": []}

@app.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        loop = asyncio.get_event_loop()
        res = await loop.run_in_executor(None, engine.run_forecast)
        return json_compatible(res)
    except: return {}

# Serving UI
if frontend_dist:
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{rest_of_path:path}")
    async def serve_ui(rest_of_path: str):
        if rest_of_path.startswith("api/") or rest_of_path.startswith("health"):
            raise HTTPException(status_code=404)
        file_path = os.path.join(frontend_dist, rest_of_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
async def root():
    if frontend_dist:
        return FileResponse(os.path.join(frontend_dist, "index.html"))
    return {"status": "ok", "message": "API Running"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
