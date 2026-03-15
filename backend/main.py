import os
import sys
import random

# CRITICAL: Path fix for services import
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
import logging
from services.forecaster import ForecastEngine
from services.valuation import ValuationService

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

def get_mock_data(ticker):
    """Generates high-quality mock data for testing or when APIs are blocked."""
    logger.info(f"Generating mock data for {ticker}")
    price = random.uniform(50, 500)
    intrinsic = price * random.uniform(0.7, 1.3)
    status = "UNDERVALUED" if intrinsic > price * 1.1 else "OVERVALUED" if intrinsic < price * 0.9 else "NEUTRAL"
    
    return {
        "ticker": ticker,
        "type": "EQUITY",
        "industry": "Artificial Intelligence / Simulation",
        "metrics": {
            "price": safe_float(price),
            "intrinsic": safe_float(intrinsic),
            "status": status,
            "eps": safe_float(random.uniform(2, 15)),
            "pe": safe_float(random.uniform(15, 40)),
            "mkt_cap": 500000000000,
            "div_annual": safe_float(random.uniform(0.5, 5.0)),
            "div_yield": safe_float(random.uniform(1.0, 4.0)),
            "beta": safe_float(random.uniform(0.8, 1.5)),
            "expense_ratio": 0.0,
            "exchange": "MOCK"
        },
        "holdings": [],
        "averages": {"pe": 25.0, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000},
        "performance": {
            "1M": round(random.uniform(-5, 5), 2),
            "YTD": round(random.uniform(-10, 20), 2),
            "1Y": round(random.uniform(5, 40), 2),
            "3Y": round(random.uniform(20, 100), 2),
            "5Y": round(random.uniform(50, 300), 2)
        },
        "peers": [{"ticker": "MOCK_PEER_1", "pe_now": 28.0, "eps_now": 5.0, "div_price_now": 1.2}],
        "info": {
            "name": f"{ticker} (Simulated Asset)",
            "summary": "This is a simulated data set generated because the live financial API is currently unavailable or the ticker is artificial. Use this for UI testing and layout verification."
        },
        "news": [{"title": "Market sentiments show positive growth for simulated assets.", "link": "#"}]
    }

@app.get("/api/analyze/{ticker}")
@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    logger.info(f"--- ANALYZING {ticker} ---")
    
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Try to get real data
        info = {}
        try:
            info = stock.info
        except: pass
        
        current_p = safe_float(getattr(stock.fast_info, 'last_price', None)) or safe_float(info.get('currentPrice'))
        
        # 2. If real data fails, use Mock Fallback
        if current_p is None:
            logger.warning(f"Live data failed for {ticker}. Using MOCK fallback.")
            return json_compatible(get_mock_data(ticker))

        # 3. Decision Logic (Real Data)
        val_service = ValuationService(ticker)
        dcf = val_service.run_dcf_model()
        intrinsic = safe_float(dcf.get('intrinsic_price')) or current_p
        
        status = "NEUTRAL"
        if intrinsic > current_p * 1.10: status = "UNDERVALUED"
        elif intrinsic < current_p * 0.90: status = "OVERVALUED"

        perf = {}
        for label, p_code in [("1M", "1mo"), ("YTD", "ytd"), ("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y")]:
            try:
                h = stock.history(period=p_code)
                if not h.empty:
                    s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                    perf[label] = round(((e - s)/s)*100, 2)
                else: perf[label] = 0.0
            except: perf[label] = 0.0

        is_etf = info.get('quoteType') == 'ETF'
        
        return json_compatible({
            "ticker": ticker,
            "type": info.get('quoteType', 'EQUITY'),
            "industry": info.get('industry') or info.get('sector') or ("Fund" if is_etf else "Finance"),
            "metrics": {
                "price": current_p, 
                "intrinsic": intrinsic, 
                "status": status,
                "eps": safe_float(info.get('trailingEps')) or 0.0, 
                "pe": safe_float(info.get('trailingPE')) or 20.0, 
                "mkt_cap": safe_float(getattr(stock.fast_info, 'market_cap', None)) or safe_float(info.get('marketCap')),
                "div_annual": safe_float(info.get('dividendRate')) or 0.0, 
                "div_yield": safe_float(info.get('dividendYield', 0) * 100) or 0.0,
                "beta": safe_float(info.get('beta')) or 1.0, 
                "expense_ratio": safe_float(info.get('trailingAnnualDividendYield')) or 0.0,
                "exchange": info.get('exchange', 'NYSE')
            },
            "holdings": [],
            "averages": {"pe": 25.0, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000},
            "performance": perf,
            "peers": [], 
            "info": {
                "name": info.get('longName', ticker), 
                "summary": info.get('longBusinessSummary', "Financial data retrieved successfully.")
            },
            "news": stock.news[:3] if hasattr(stock, 'news') and stock.news else []
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        # Global fallback to mock so the UI NEVER breaks
        return json_compatible(get_mock_data(ticker))

@app.get("/api/history/{ticker}")
@app.get("/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk")):
    try:
        stock = yf.Ticker(ticker.upper())
        interval = "1d"
        if period == "1d": interval = "1h"
        elif period in ["5d", "1wk"]: interval = "30m"
        hist = stock.history(period=period, interval=interval).reset_index()
        
        if hist.empty:
            # Mock History Generator
            logger.warning(f"No history for {ticker}. Generating mock history.")
            dates = pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
            data = [{"date": d.strftime('%m-%d %H:%M'), "price": 100 + random.uniform(-5, 5)} for d in dates]
            return {"data": data, "zones": {"support": {"low": 90, "high": 95}, "resistance": {"low": 105, "high": 110}}, "performance": {"is_positive": True, "pct": 5.0}}

        col = 'Date' if 'Date' in hist.columns else 'Datetime'
        hist['date'] = hist[col].dt.strftime('%m-%d %H:%M')
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        lows, highs = hist['Low'].min(), hist['High'].max()
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": lows * 0.99, "high": lows * 1.01}, "resistance": {"low": highs * 0.99, "high": highs * 1.01}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
        })
    except: 
        return {"data": []}

@app.get("/api/forecast/{ticker}")
@app.get("/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        result = engine.run_forecast()
        if not result:
            # Mock Forecast Generator
            return {
                "history": [{"date": "2024-01-01", "price": 100}],
                "hybrid": [{"date": "2024-01-02", "price": 105}],
                "baseline": [{"date": "2024-01-02", "price": 102}]
            }
        return json_compatible(result)
    except: return {}

# UI SERVER LOGIC
frontend_dist = os.path.abspath(os.path.join(current_dir, "..", "frontend", "dist"))

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("health"):
            return None
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"status": "ok", "message": "API Running."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
