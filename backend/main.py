import os
import sys

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

@app.get("/api/analyze/{ticker}")
@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    logger.info(f"--- START ANALYSIS FOR {ticker} ---")
    
    try:
        # Create Ticker instance
        # We don't pass session here to keep it simple, but yfinance often needs it on Render
        stock = yf.Ticker(ticker)
        
        # 1. Fetch Info (Primary Data Source)
        try:
            info = stock.info
            if not info or len(info) < 5:
                logger.warning(f"yfinance returned empty info for {ticker}. Likely blocked or invalid ticker.")
                info = {}
        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            info = {}

        # 2. Fetch Price (Multiple Fallbacks)
        current_p = safe_float(info.get('currentPrice')) or safe_float(info.get('regularMarketPrice'))
        
        if current_p is None:
            logger.info(f"Price not in info for {ticker}, trying fast_info...")
            try:
                current_p = safe_float(stock.fast_info.last_price)
            except: pass
            
        if current_p is None:
            logger.info(f"Price still missing, trying 1d history...")
            try:
                hist = stock.history(period="1d")
                if not hist.empty:
                    current_p = safe_float(hist['Close'].iloc[-1])
            except: pass

        # FINAL ERROR: If we can't get a price, we can't analyze.
        if current_p is None:
            logger.error(f"COULD NOT RESOLVE PRICE FOR {ticker}")
            raise HTTPException(status_code=404, detail=f"Data for {ticker} is temporarily unavailable. Yahoo Finance may be blocking the request.")

        # 3. Valuation & Logic
        val_service = ValuationService(ticker)
        dcf = val_service.run_dcf_model()
        intrinsic = safe_float(dcf.get('intrinsic_price')) or current_p
        
        # Determine Status
        status = "NEUTRAL"
        if intrinsic > current_p * 1.10: status = "UNDERVALUED"
        elif intrinsic < current_p * 0.90: status = "OVERVALUED"

        # 4. Performance
        perf = {}
        periods = [("1M", "1mo"), ("YTD", "ytd"), ("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y")]
        for label, p_code in periods:
            try:
                h = stock.history(period=p_code)
                if not h.empty:
                    s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                    perf[label] = round(((e - s)/s)*100, 2)
            except: perf[label] = 0.0

        # 5. Metadata
        is_etf = info.get('quoteType') == 'ETF'
        industry = info.get('industry') or info.get('sector') or ("Exchange Traded Fund" if is_etf else "Finance/Other")
        
        # 6. Build Clean Response
        response_data = {
            "ticker": ticker,
            "type": info.get('quoteType', 'EQUITY'),
            "industry": industry,
            "metrics": {
                "price": current_p, 
                "intrinsic": intrinsic, 
                "status": status,
                "eps": safe_float(info.get('trailingEps')), 
                "pe": safe_float(info.get('trailingPE')), 
                "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(info.get('dividendRate')) or 0.0, 
                "div_yield": safe_float(info.get('dividendYield', 0) * 100) or 0.0,
                "beta": safe_float(info.get('beta')), 
                "expense_ratio": safe_float(info.get('trailingAnnualDividendYield')) or 0.0, # Placeholder if missing
                "exchange": info.get('exchange')
            },
            "holdings": [], # ETFs would need more complex scraping
            "averages": {
                "pe": 25.0, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000
            },
            "performance": perf,
            "peers": [], 
            "info": {
                "name": info.get('longName', ticker), 
                "summary": info.get('longBusinessSummary', "No detailed description available at this time.")
            },
            "news": stock.news[:3] if hasattr(stock, 'news') and stock.news else []
        }
        
        logger.info(f"SUCCESS: Analysis complete for {ticker}")
        return json_compatible(response_data)

    except HTTPException: raise
    except Exception as e:
        logger.error(f"GLOBAL ERROR in /analyze/{ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred while fetching data.")

@app.get("/api/history/{ticker}")
@app.get("/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk")):
    try:
        stock = yf.Ticker(ticker.upper())
        interval = "1d"
        if period == "1d": interval = "1h"
        elif period in ["5d", "1wk"]: interval = "30m"
        hist = stock.history(period=period, interval=interval).reset_index()
        if hist.empty: return {"data": []}
        col = 'Date' if 'Date' in hist.columns else 'Datetime'
        hist['date'] = hist[col].dt.strftime('%m-%d %H:%M')
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        lows, highs = hist['Low'].min(), hist['High'].max()
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": lows * 0.99, "high": lows * 1.01}, "resistance": {"low": highs * 0.99, "high": highs * 1.01}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
        })
    except: return {"data": []}

@app.get("/api/forecast/{ticker}")
@app.get("/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        return json_compatible(engine.run_forecast())
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
    return {"status": "ok", "message": "API Running. UI build not found."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
