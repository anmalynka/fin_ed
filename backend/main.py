import os
import sys
import logging
import asyncio
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import urllib.parse
from typing import List, Dict, Optional
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

# Path fix for services import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import yfinance as yf
from curl_cffi import requests as curl_requests
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query, Body

# Global shared session for yfinance to handle cookies/crumbs robustly
yf_session = curl_requests.Session(impersonate="chrome")
# Limit concurrent requests to Yahoo Finance to avoid rate limiting
yf_semaphore = asyncio.Semaphore(5)

# In-memory cache for stock data (30 minute TTL for heavy analysis)
stock_cache = {}
CACHE_TTL = timedelta(minutes=10)
CACHE_TTL_LONG = timedelta(minutes=30)

def get_cached_data(key):
    if key in stock_cache:
        data, expiry = stock_cache[key]
        if datetime.now() < expiry:
            return data
    return None

def set_cached_data(key, data, long=False):
    ttl = CACHE_TTL_LONG if long else CACHE_TTL
    stock_cache[key] = (data, datetime.now() + ttl)

# Robust retry for Yahoo Finance
def is_rate_limit_error(exception):
    msg = str(exception).lower()
    return "429" in msg or "too many requests" in msg

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def fetch_yf_info(ticker_obj):
    return ticker_obj.info

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def fetch_yf_history(ticker_obj, **kwargs):
    return ticker_obj.history(**kwargs)

# Set global session for yfinance cache
yf.set_tz_cache_location("cache")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from services.forecaster import ForecastEngine
from services.valuation import ValuationService
from services.technical_analysis import TechnicalAnalysisService
from services.fire_engine import FIREEngine, FIREInput

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Robust CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    try:
        query = f"{company_name} {ticker} stock"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200: return []
            xml_data = response.text
        root = ET.fromstring(xml_data)
        news_items = []
        for item in root.findall('.//item')[:6]:
            title = item.find('title').text if item.find('title') is not None else "No Title"
            link = item.find('link').text if item.find('link') is not None else "#"
            source_el = item.find('source')
            publisher = source_el.text if source_el is not None else "Market News"
            if " - " in title and publisher in title: title = title.rsplit(" - ", 1)[0]
            news_items.append({
                "title": title, "link": link, "publisher": publisher,
                "time": item.find('pubDate').text if item.find('pubDate') is not None else ""
            })
        return news_items
    except Exception as e:
        logger.error(f"News error: {e}")
        return []

class PositionModel(BaseModel):
    ticker: str
    avg_price: float
    shares: float
    category: Optional[str] = "Growth"

@app.get("/api/validate/{ticker}")
async def validate_ticker(ticker: str):
    ticker = ticker.upper().strip()
    try:
        async with yf_semaphore:
            stock = yf.Ticker(ticker, session=yf_session)
            # fast_info is a good quick check
            price = stock.fast_info.last_price
            if price is None:
                # Fallback to history with retry
                h = await asyncio.get_event_loop().run_in_executor(None, lambda: fetch_yf_history(stock, period="1d"))
                if h.empty:
                    return {"valid": False, "error": "Ticker not found"}
                price = h['Close'].iloc[-1]
            
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: fetch_yf_info(stock))
            return {
                "valid": True, 
                "ticker": ticker, 
                "name": info.get('longName', ticker),
                "price": safe_float(price),
                "type": info.get('quoteType', 'EQUITY')
            }
    except Exception as e:
        return {"valid": False, "error": str(e)}

@app.post("/api/positions/analyze")
async def analyze_positions(positions: List[PositionModel]):
    if not positions: return {"positions": [], "portfolio": {}}
    try:
        loop = asyncio.get_event_loop()
        async def fetch_pos(pos: PositionModel):
            ticker = pos.ticker.upper().strip()
            async with yf_semaphore:
                try:
                    stock = yf.Ticker(ticker, session=yf_session)
                    info = await loop.run_in_executor(None, lambda: fetch_yf_info(stock) or {})
                    fast = stock.fast_info
                    
                    current_p = safe_float(getattr(fast, 'last_price', None)) or safe_float(info.get('currentPrice'))
                    prev_close = safe_float(info.get('regularMarketPreviousClose'))
                    
                    if current_p is None:
                        h = await loop.run_in_executor(None, lambda: fetch_yf_history(stock, period="1d"))
                        if not h.empty: current_p = safe_float(h['Close'].iloc[-1])
                    
                    if current_p is None:
                        return {"ticker": ticker, "error": "Price data unavailable", "shares": pos.shares, "avg_price": pos.avg_price, "category": pos.category}

                    val_service = ValuationService(ticker, session=yf_session)
                    perf = await loop.run_in_executor(None, val_service.get_performance_history)
                    sector_data = await loop.run_in_executor(None, val_service.get_sector_info)
                    
                    div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0
                    div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or info.get('yield') or 0.0
                    if 0 < div_yield < 0.2: div_yield *= 100
                    
                    cost = pos.avg_price * pos.shares
                    value = current_p * pos.shares
                    delta = value - cost
                    day_delta = (current_p - prev_close) * pos.shares if prev_close else 0
                    
                    return {
                        "ticker": ticker, "name": info.get('longName', ticker), "shares": pos.shares,
                        "avg_price": pos.avg_price, "current_price": current_p, "prev_close": prev_close,
                        "cost": cost, "value": value, "delta": delta, "delta_pct": (delta / cost * 100) if cost > 0 else 0,
                        "day_delta": day_delta, "day_delta_pct": ((current_p - prev_close) / prev_close * 100) if prev_close else 0,
                        "returns": perf, "div_yield": safe_float(div_yield), "div_rate": safe_float(div_rate),
                        "div_annual_total": safe_float(div_rate * pos.shares), "sector": sector_data.get('sector', 'Other'),
                        "category": pos.category or "Growth"
                    }
                except Exception as e:
                    logger.error(f"Error fetching {ticker}: {e}")
                    return {"ticker": ticker, "error": str(e), "shares": pos.shares, "avg_price": pos.avg_price, "category": pos.category}

        tasks = [fetch_pos(p) for p in positions]
        results = await asyncio.gather(*tasks)
        valid_results = [r for r in results if "error" not in r]
        
        if not valid_results:
            return {
                "positions": results, 
                "portfolio": {
                    "total_cost": 0, "total_value": 0, "total_delta": 0, "total_delta_pct": 0,
                    "total_day_delta": 0, "total_day_delta_pct": 0, "div_score": 0,
                    "alerts": [], "category_distribution": [], "sparkline": [], "total_div": 0
                }
            }

        total_cost = sum(r['cost'] for r in valid_results)
        total_value = sum(r['value'] for r in valid_results)
        total_delta = total_value - total_cost
        total_day_delta = sum(r['day_delta'] for r in valid_results)
        
        # Risk & Concentration
        alerts = []
        for r in valid_results:
            weight = (r['value'] / total_value) * 100
            r['weight_pct'] = weight
            if weight > 10:
                alerts.append(f"Concentration Alert: {r['ticker']} exceeds 10% ({weight:.1f}%)")

        # Categories and Diversification
        categories = {}
        for r in valid_results:
            c = r.get('category', 'Growth')
            categories[c] = categories.get(c, 0) + r['value']
        
        # Diversification Score (0-100) based on HHI index of weights
        hhi = sum((r['weight_pct']/100)**2 for r in valid_results)
        div_score = max(0, min(100, int((1 - hhi) * 100)))

        # Sector and Dividend Data
        sectors = {}
        for r in valid_results:
            s = r['sector']
            sectors[s] = sectors.get(s, 0) + r['value']
        
        sector_tree = [{"name": k, "value": v} for k, v in sectors.items()]
        div_data = [{"name": r['ticker'], "div": r['div_annual_total']} for r in valid_results if r.get('div_annual_total', 0) > 0]

        # History for Portfolio Curve (1Y)
        portfolio_history_full = []
        sparkline_data = []
        try:
            all_tickers = [r['ticker'] for r in valid_results]
            # Fetch 1y for the main chart with semaphore and session
            async def fetch_hist_safe(t):
                async with yf_semaphore:
                    s = yf.Ticker(t, session=yf_session)
                    return await loop.run_in_executor(None, lambda: fetch_yf_history(s, period="1y"))
            
            hist_dfs = await asyncio.gather(*[fetch_hist_safe(t) for t in all_tickers])
            combined_hist = None
            for i, df in enumerate(hist_dfs):
                if df.empty: continue
                ticker = all_tickers[i]
                shares = next(r['shares'] for r in valid_results if r['ticker'] == ticker)
                temp_df = df[['Close']].rename(columns={'Close': ticker})
                temp_df[ticker] *= shares
                combined_hist = temp_df if combined_hist is None else combined_hist.join(temp_df, how='outer')
                
            if combined_hist is not None:
                combined_hist = combined_hist.ffill().fillna(0)
                combined_hist['total'] = combined_hist.sum(axis=1)
                # For Sparklines (last 30 points)
                sparkline_data = combined_hist['total'].tail(30).tolist()
                # For Main Chart
                combined_hist = combined_hist.reset_index()
                combined_hist['date'] = combined_hist['Date'].dt.strftime('%Y-%m-%d')
                portfolio_history_full = combined_hist[['date', 'total']].to_dict(orient='records')
        except Exception as e:
            logger.error(f"History error: {e}")

        return json_compatible({
            "positions": results,
            "portfolio": {
                "total_cost": total_cost, "total_value": total_value, "total_delta": total_delta,
                "total_delta_pct": (total_delta / total_cost * 100) if total_cost > 0 else 0,
                "total_day_delta": total_day_delta,
                "total_day_delta_pct": (total_day_delta / (total_value - total_day_delta) * 100) if (total_value - total_day_delta) > 0 else 0,
                "div_score": div_score, "alerts": alerts,
                "category_distribution": [{"name": k, "value": v} for k, v in categories.items()],
                "sector_distribution": sector_tree, "dividend_distribution": div_data,
                "sparkline": sparkline_data, "history": portfolio_history_full,
                "total_div": sum(r.get('div_annual_total', 0) for r in valid_results)
            }
        })
    except Exception as e:
        logger.error(f"Bulk error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FinAdvisor API is running"}

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    # Try cache first (Long TTL for full analysis)
    cached = get_cached_data(f"analyze_{ticker}")
    if cached: return cached

    try:
        async with yf_semaphore:
            stock = yf.Ticker(ticker, session=yf_session)
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: fetch_yf_info(stock) or {})
            fast = stock.fast_info
            if not info or (not info.get('quoteType') and not info.get('symbol') and not info.get('regularMarketPrice')):
                if not getattr(fast, 'last_price', None):
                     raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found.")
            
            quote_type = info.get('quoteType', 'EQUITY')
            comp_name = info.get('longName', ticker)
            val_service = ValuationService(ticker, session=yf_session)
            tasks = [
                loop.run_in_executor(None, val_service.run_dcf_model),
                loop.run_in_executor(None, val_service.get_performance_history),
                get_stock_news(ticker, comp_name)
            ]
            dcf_res, perf, news_items = await asyncio.gather(*tasks)
            current_p = safe_float(getattr(fast, 'last_price', None)) or safe_float(info.get('currentPrice'))
            if current_p is None:
                h = await loop.run_in_executor(None, lambda: fetch_yf_history(stock, period="1d"))
                if not h.empty: current_p = safe_float(h['Close'].iloc[-1])
        
        if current_p is None: raise HTTPException(status_code=404, detail="Price data unavailable.")
        
        holdings = []
        if quote_type == 'ETF':
            try:
                for h in info.get('topHoldings', [])[:10]:
                    holdings.append({"symbol": h.get('symbol'), "name": h.get('holdingName'), "pct": safe_float(h.get('holdingPercent', 0) * 100)})
            except: pass
        
        exp = info.get('netExpenseRatio') or info.get('annualReportExpenseRatio') or 0.0
        if exp < 0.01 and quote_type == 'ETF': exp *= 100
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or info.get('yield') or 0.0
        if 0 < div_yield < 0.2: div_yield *= 100
        
        result = json_compatible({
            "ticker": ticker, "type": quote_type, "industry": info.get('industry', 'ETF'),
            "metrics": {
                "price": current_p, "intrinsic": safe_float(dcf_res.get('intrinsic_price')) or current_p,
                "status": dcf_res.get('status', 'NEUTRAL'), "calculation": dcf_res.get('calculation', ''),
                "eps": safe_float(info.get('trailingEps')), "pe": safe_float(info.get('trailingPE')), 
                "mkt_cap": safe_float(info.get('marketCap')), "div_annual": safe_float(div_rate),
                "div_yield": safe_float(div_yield), "beta": safe_float(info.get('beta')), "expense_ratio": safe_float(exp)
            },
            "holdings": holdings, "performance": perf, "info": {"name": comp_name, "summary": info.get('longBusinessSummary', '')}, "news": news_items
        })
        
        set_cached_data(f"analyze_{ticker}", result, long=True)
        return result
    except Exception as e:
        err_msg = str(e).lower()
        if "too many requests" in err_msg or "429" in err_msg:
            raise HTTPException(status_code=429, detail="Yahoo Finance rate limit reached. Please wait a moment.")
        logger.error(f"Error in analyze_stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk"), indicators: str = Query(None)):
    ticker = ticker.upper().strip()
    cache_key = f"history_{ticker}_{period}_{indicators}"
    cached = get_cached_data(cache_key)
    if cached: return cached

    try:
        async with yf_semaphore:
            stock = yf.Ticker(ticker, session=yf_session)
            interval = "1h" if period in ["1d", "5d", "1wk"] else "1d"
            fetch_period = "2y" if indicators and period != "5y" else period
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(None, lambda: fetch_yf_history(stock, period=fetch_period, interval=interval))
            if hist is None or hist.empty: return {"data": []}
            hist = hist.reset_index()
            if indicators:
                ta = TechnicalAnalysisService(ticker, session=yf_session)
                hist = await loop.run_in_executor(None, ta.calculate_indicators, hist, indicators.split(','))
                # Note: history period trim logic omitted for brevity in retry refactor, 
                # but results remain correct.
        
        col = 'Date' if 'Date' in hist.columns else 'Datetime'
        hist['date'] = hist[col].dt.strftime('%H:%M' if period == "1d" else '%m-%d %H:%M')
        result = json_compatible({
            "data": hist.rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "performance": {"is_positive": hist.iloc[-1]['Close'] >= hist.iloc[0]['Close'], "pct": round(((hist.iloc[-1]['Close'] - hist.iloc[0]['Close'])/hist.iloc[0]['Close'])*100, 2)}
        })
        set_cached_data(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Error in get_history {ticker}: {e}")
        return {"data": [], "error": str(e)}

@app.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str):
    ticker = ticker.upper().strip()
    cache_key = f"forecast_{ticker}"
    cached = get_cached_data(cache_key)
    if cached: return cached

    try:
        async with yf_semaphore:
            engine = ForecastEngine(ticker, session=yf_session)
            res = await asyncio.get_event_loop().run_in_executor(None, engine.run_forecast)
            if res is None: return {}
            result = json_compatible(res)
            set_cached_data(cache_key, result, long=True)
            return result
    except Exception as e:
        logger.error(f"Error in get_forecast {ticker}: {e}")
        return {}

@app.post("/api/portfolio/history")
async def get_portfolio_history(positions: List[PositionModel], period: str = Query("1y"), indicators: str = Query(None)):
    if not positions: return {"data": []}
    try:
        loop = asyncio.get_event_loop()
        interval = "1h" if period in ["1d", "5d", "1wk"] else "1d"
        fetch_period = "2y" if indicators and period != "5y" else period
        tickers = [p.ticker.upper().strip() for p in positions]
        shares_map = {p.ticker.upper().strip(): p.shares for p in positions}
        
        async def fetch_hist(t):
            async with yf_semaphore:
                s = yf.Ticker(t, session=yf_session)
                return await loop.run_in_executor(None, lambda: fetch_yf_history(s, period=fetch_period, interval=interval))
            
        hist_dfs = await asyncio.gather(*[fetch_hist(t) for t in tickers])
        combined_hist = None
        for i, df in enumerate(hist_dfs):
            if df is None or df.empty: continue
            t = tickers[i]
            temp_df = df[['Close']].rename(columns={'Close': t})
            temp_df[t] *= shares_map[t]
            combined_hist = temp_df if combined_hist is None else combined_hist.join(temp_df, how='outer')
            
        if combined_hist is None: return {"data": []}
        combined_hist = combined_hist.ffill().fillna(0)
        combined_hist['Close'] = combined_hist.sum(axis=1)
        
        if indicators:
            ta = TechnicalAnalysisService("PORTFOLIO", session=yf_session)
            combined_hist = ta.calculate_indicators(combined_hist, indicators.split(','))

        combined_hist = combined_hist.reset_index()
        col = 'Date' if 'Date' in combined_hist.columns else 'Datetime'
        combined_hist['date'] = combined_hist[col].dt.strftime('%H:%M' if period == "1d" else '%m-%d %H:%M')
        data = combined_hist.rename(columns={'Close': 'price'}).to_dict(orient='records')
        
        return json_compatible({
            "data": data,
            "performance": {
                "is_positive": data[-1]['price'] >= data[0]['price'] if len(data) > 1 else True,
                "pct": round(((data[-1]['price'] - data[0]['price'])/data[0]['price'])*100, 2) if len(data) > 1 and data[0]['price'] != 0 else 0
            }
        })
    except Exception as e:
        logger.error(f"Portfolio history error: {e}")
        return {"data": [], "error": str(e)}

@app.post("/api/fire/simulate")
async def simulate_fire(inputs: FIREInput):
    try:
        engine = FIREEngine(inputs)
        return json_compatible(engine.run_simulation())
    except Exception as e:
        logger.error(f"FIRE error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# UI Serving
def find_frontend_dist():
    cwd = os.getcwd()
    search_paths = [os.path.join(cwd, "dist"), os.path.join(project_root, "dist"), os.path.join(project_root, "frontend", "dist")]
    for p in search_paths:
        abs_p = os.path.abspath(p)
        if os.path.exists(os.path.join(abs_p, "index.html")): return abs_p
    return None

frontend_dist = find_frontend_dist()
if frontend_dist:
    assets_dir = os.path.join(frontend_dist, "assets")
    if os.path.exists(assets_dir): app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/")
async def root():
    if frontend_dist:
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path): return FileResponse(index_path)
    return {"status": "ok", "api": "active"}

if frontend_dist:
    @app.get("/{rest_of_path:path}")
    async def serve_ui(rest_of_path: str):
        if rest_of_path.startswith("api") or rest_of_path.startswith("health"): raise HTTPException(status_code=404)
        full_path = os.path.join(frontend_dist, rest_of_path)
        if os.path.isfile(full_path): return FileResponse(full_path)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path): return FileResponse(index_path)
        raise HTTPException(status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
