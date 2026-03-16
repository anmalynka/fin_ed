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
    price = random.uniform(150, 350)
    intrinsic = price * random.uniform(0.8, 1.2)
    return {
        "ticker": ticker,
        "type": "EQUITY",
        "industry": "Technology / Analytics",
        "metrics": {
            "price": safe_float(price), "intrinsic": safe_float(intrinsic), "status": "NEUTRAL",
            "eps": 5.42, "pe": 28.5, "mkt_cap": 250000000000,
            "div_annual": 1.20, "div_yield": 0.8, "beta": 1.15, "expense_ratio": 0.0, "exchange": "NYSE"
        },
        "holdings": [],
        "averages": {"pe": 25.0, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000},
        "performance": {"1M": 2.5, "YTD": 12.4, "1Y": 25.1, "3Y": 45.0, "5Y": 120.0},
        "peers": [], 
        "info": {"name": f"{ticker} Corp", "summary": "Live data retrieval is temporarily restricted. Showing simulated institutional metrics for UI verification."},
        "news": []
    }

# --- API ROUTES FIRST ---

@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FinAdvisor API is running"}

@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        current_p = safe_float(getattr(stock.fast_info, 'last_price', None)) or safe_float(info.get('currentPrice'))
        
        if current_p is None:
            return json_compatible(get_mock_data(ticker))

        val_service = ValuationService(ticker)
        dcf = val_service.run_dcf_model()
        intrinsic = safe_float(dcf.get('intrinsic_price')) or current_p
        
        return json_compatible({
            "ticker": ticker,
            "type": info.get('quoteType', 'EQUITY'),
            "industry": info.get('industry') or "Finance",
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": "NEUTRAL",
                "eps": safe_float(info.get('trailingEps')) or 0.0, 
                "pe": safe_float(info.get('trailingPE')) or 20.0, 
                "mkt_cap": safe_float(getattr(stock.fast_info, 'market_cap', None)) or safe_float(info.get('marketCap')),
                "div_annual": safe_float(info.get('dividendRate')) or 0.0, 
                "div_yield": safe_float(info.get('dividendYield', 0) * 100) or 0.0,
                "beta": safe_float(info.get('beta')) or 1.0, 
                "expense_ratio": 0.0, "exchange": info.get('exchange', 'NYSE')
            },
            "holdings": [],
            "averages": {"pe": 25.0, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000},
            "performance": {"1M": 0, "YTD": 0, "1Y": 0, "3Y": 0, "5Y": 0},
            "peers": [], 
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', "")},
            "news": []
        })
    except:
        return json_compatible(get_mock_data(ticker))

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk")):
    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period).reset_index()
        if hist.empty: return {"data": []}
        hist['date'] = hist['Date'].dt.strftime('%m-%d %H:%M')
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": 0, "high": 0}, "resistance": {"low": 0, "high": 0}},
            "performance": {"is_positive": True, "pct": 0}
        })
    except: return {"data": []}

@app.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        return json_compatible(engine.run_forecast())
    except: return {}

# --- STATIC FILES LAST ---

frontend_dist = os.path.abspath(os.path.join(current_dir, "..", "frontend", "dist"))

if os.path.exists(frontend_dist):
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    # Catch-all for UI
    @app.get("/{rest_of_path:path}")
    async def serve_ui(request: Request, rest_of_path: str):
        # Explicitly ignore API calls
        if rest_of_path.startswith("api/") or rest_of_path.startswith("health"):
            raise HTTPException(status_code=404)
            
        # Check if it's a file
        file_path = os.path.join(frontend_dist, rest_of_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Default to index.html
        return FileResponse(os.path.join(frontend_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
