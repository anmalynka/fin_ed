import os
import sys
import random

# CRITICAL: Path fix for services import
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
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
    logger.error("COULD NOT FIND FRONTEND DIST IN ANY KNOWN LOCATION")
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

<<<<<<< HEAD
@app.get("/api/debug-paths")
async def debug_paths():
    return {
        "current_dir": current_dir,
        "project_root": project_root,
        "frontend_dist_found": frontend_dist,
        "exists": os.path.exists(frontend_dist) if frontend_dist else False,
        "contents": os.listdir(frontend_dist) if frontend_dist and os.path.exists(frontend_dist) else []
    }

@app.get("/api/health")
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "FinAdvisor API is running"}

=======
>>>>>>> feature/new-edit
@app.get("/api/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        current_p = safe_float(getattr(stock.fast_info, 'last_price', None)) or safe_float(info.get('currentPrice'))
        
<<<<<<< HEAD
        if current_p is None:
            # Try history as last resort
            h = stock.history(period="1d")
            if not h.empty:
                current_p = safe_float(h['Close'].iloc[-1])

        if current_p is None:
            raise HTTPException(status_code=404, detail="Ticker not found")

        val_service = ValuationService(ticker)
        dcf = val_service.run_dcf_model()
        intrinsic = safe_float(dcf.get('intrinsic_price')) or (current_p * 1.1)
        status = dcf.get('status', 'NEUTRAL')
        calculation = dcf.get('calculation', "")
        comment = dcf.get('comment', "")
        error = dcf.get('error')
        industry_pe = safe_float(dcf.get('industry_pe')) or 20.0
        
        # Real Performance Data
        performance = val_service.get_performance_history()
        
        # Dividend & Expense Ratio Logic
        div_annual = safe_float(info.get('dividendRate')) or safe_float(info.get('trailingAnnualDividendRate')) or 0.0
        div_yield = safe_float(info.get('dividendYield')) or safe_float(info.get('trailingAnnualDividendYield')) or safe_float(info.get('yield')) or 0.0
        
        # yfinance yield can be 0.033 (decimal) or 3.3 (percent). 
        if div_yield and div_yield < 0.2: div_yield *= 100
        
        # CRITICAL FALLBACK: If div_annual is 0 but yield exists, calculate it
        if div_annual == 0 and div_yield > 0 and current_p:
            div_annual = round((div_yield / 100) * current_p, 2)
        
        expense_ratio = safe_float(info.get('netExpenseRatio'))
        # Expense ratios are usually very small (e.g., 0.03% or 0.09%).
        if expense_ratio and expense_ratio < 0.01: expense_ratio *= 100
=======
        # Rigorous check for ticker existence
        if not info or (not info.get('quoteType') and not info.get('symbol') and not info.get('regularMarketPrice')):
            if not getattr(fast, 'last_price', None):
                 raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' not found or has no public data.")

        quote_type = info.get('quoteType', 'EQUITY')
        is_etf = quote_type == 'ETF'
        
        current_p = safe_float(getattr(fast, 'last_price', None)) or safe_float(info.get('currentPrice'))
        if current_p is None:
            h = stock.history(period="1d")
            if not h.empty: current_p = safe_float(h['Close'].iloc[-1])
        
        if current_p is None:
            raise HTTPException(status_code=404, detail=f"Ticker '{ticker}' price data unavailable.")

        # 1. ETF Specific Data: Holdings
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

        # 2. Valuation Logic
        val_service = ValuationService(ticker)
        dcf_res = val_service.run_dcf_model()
        intrinsic = safe_float(dcf_res.get('intrinsic_price')) or current_p
        status = dcf_res.get('status', 'NEUTRAL')
        calculation = dcf_res.get('calculation', '')
        error = dcf_res.get('error')
        industry_pe = safe_float(dcf_res.get('industry_pe')) or 20.0

        # 3. Dividend & Expense Ratio
        exp = info.get('netExpenseRatio') or info.get('annualReportExpenseRatio') or info.get('expenseRatio')
        if exp is None and is_etf:
            try:
                fd = stock.funds_data
                if fd and not fd.fund_operations.empty:
                    exp = fd.fund_operations.loc['Annual Report Expense Ratio'].iloc[0]
            except: pass
        
        if exp and exp < 0.01: exp *= 100
        if exp is None: exp = 0.0
        
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or info.get('yield') or 0.0
        if 0 < div_yield < 0.2: div_yield *= 100
        if (not div_rate or div_rate == 0) and div_yield > 0: div_rate = (div_yield / 100) * current_p

        # 4. Performance Data
        perf = val_service.get_performance_history()
>>>>>>> feature/new-edit

        return json_compatible({
            "ticker": ticker,
            "type": info.get('quoteType', 'EQUITY'),
            "industry": info.get('industry') or "Finance",
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
<<<<<<< HEAD
                "calculation": calculation, "comment": comment, "error": error,
                "eps": safe_float(info.get('trailingEps')) or 0.0, 
                "pe": safe_float(info.get('trailingPE')) or 20.0, 
                "mkt_cap": safe_float(info.get('marketCap')) or 1000000000,
                "div_annual": div_annual, 
                "div_yield": div_yield,
                "beta": safe_float(info.get('beta')) or 1.0, 
                "expense_ratio": expense_ratio or 0.0, 
                "exchange": info.get('exchange', 'NYSE')
            },
            "holdings": [],
            "averages": {"pe": industry_pe, "eps": 4.5, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 100000000000},
            "performance": performance,
            "peers": [], 
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', "")},
            "news": []
=======
                "calculation": calculation, "error": error,
                "eps": safe_float(info.get('trailingEps')), "pe": safe_float(info.get('trailingPE')), 
                "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(div_rate), "div_yield": safe_float(div_yield),
                "beta": safe_float(info.get('beta')), "expense_ratio": safe_float(exp), "exchange": info.get('exchange')
            },
            "holdings": holdings,
            "averages": {"pe": industry_pe, "eps": 4.2, "div": 1.5, "risk": 1.1, "exp": 0.45, "mkt": 150000000000},
            "performance": perf,
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', '')},
            "news": stock.news[:3] if stock.news else []
>>>>>>> feature/new-edit
        })
    except HTTPException: raise
    except Exception as e:
<<<<<<< HEAD
        logger.error(f"Error in analyze: {e}")
=======
        logger.error(f"Error: {e}")
>>>>>>> feature/new-edit
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk")):
    try:
        # Intelligently select interval
        interval = "1d"
        if period == "1d": interval = "1h"
<<<<<<< HEAD
        elif period == "5d": interval = "1h"
        elif period == "1mo": interval = "1d"
        
        stock = yf.Ticker(ticker.upper())
=======
        elif period in ["5d", "1wk"]: interval = "1h"
>>>>>>> feature/new-edit
        hist = stock.history(period=period, interval=interval).reset_index()
        if hist.empty: return {"data": []}
        
        # Calculate percentage change for the period
        first_p = hist['Close'].iloc[0]
        last_p = hist['Close'].iloc[-1]
        pct = round(((last_p - first_p) / first_p) * 100, 2)
        is_pos = pct >= 0

        # Use 'Date' or 'Datetime' depending on period
        col = 'Date' if 'Date' in hist.columns else 'Datetime'
<<<<<<< HEAD
=======
        
>>>>>>> feature/new-edit
        if period == "1d":
            hist['date'] = hist[col].dt.strftime('%H:%M')
        else:
            hist['date'] = hist[col].dt.strftime('%m-%d %H:%M')
<<<<<<< HEAD
        
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": 0, "high": 0}, "resistance": {"low": 0, "high": 0}},
            "performance": {"is_positive": is_pos, "pct": pct}
=======
            
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": 0, "high": 0}, "resistance": {"low": 0, "high": 0}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
>>>>>>> feature/new-edit
        })
    except: return {"data": []}

@app.get("/api/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        return json_compatible(engine.run_forecast())
    except: return {}

# --- STATIC FILES / UI SERVING (MUST BE LAST) ---

if frontend_dist:
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    @app.get("/{rest_of_path:path}")
    async def serve_ui(rest_of_path: str):
        # 1. If it's an API route, don't handle it here
        if rest_of_path.startswith("api/") or rest_of_path.startswith("health"):
            raise HTTPException(status_code=404)
            
        # 2. Check if it's a specific file (favicon, etc)
        file_path = os.path.join(frontend_dist, rest_of_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # 3. Default to index.html
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
async def root():
    if frontend_dist:
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"status": "ok", "message": "API Running. UI files not found in frontend/dist."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
