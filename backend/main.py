from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import sys
from services.forecaster import ForecastEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/")
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "FinAdvisor API is running"}

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
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        fast = stock.fast_info
        
        quote_type = info.get('quoteType', 'EQUITY')
        is_etf = quote_type == 'ETF'
        
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

        exp = info.get('netExpenseRatio') or info.get('annualReportExpenseRatio') or info.get('expenseRatio')
        if exp is None and is_etf:
            try:
                fd = stock.funds_data
                if fd and not fd.fund_operations.empty:
                    exp = fd.fund_operations.loc['Annual Report Expense Ratio'].iloc[0]
                    if exp and exp < 0.01: exp *= 100
            except: pass
        if exp is None: exp = 0.0
        
        div_rate = info.get('dividendRate') or info.get('trailingAnnualDividendRate') or 0.0
        div_yield = info.get('dividendYield') or info.get('trailingAnnualDividendYield') or info.get('yield') or 0.0
        if 0 < div_yield < 0.1: div_yield *= 100
        current_p = safe_float(fast.last_price) or safe_float(info.get('currentPrice'))
        if (not div_rate or div_rate == 0) and div_yield > 0 and current_p: div_rate = (div_yield / 100) * current_p

        eps = safe_float(info.get('trailingEps'))
        growth = info.get('earningsGrowth') or 0.15
        intrinsic = abs(eps * (growth * 100)) if eps else current_p
        
        status = "NEUTRAL"
        if intrinsic > current_p * 1.05: status = "UNDERVALUED"
        elif intrinsic < current_p * 0.95: status = "OVERVALUED"

        perf = {}
        for p in [("1M", "1mo"), ("YTD", "ytd"), ("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y")]:
            h = stock.history(period=p[1])
            if not h.empty:
                s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                perf[p[0]] = round(((e - s)/s)*100, 2)

        return json_compatible({
            "ticker": ticker,
            "type": quote_type,
            "industry": info.get('industry', 'Exchange Traded Fund'),
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
                "eps": eps, "pe": safe_float(info.get('trailingPE')), "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(div_rate), "div_yield": safe_float(div_yield),
                "beta": safe_float(info.get('beta')), "expense_ratio": safe_float(exp), "exchange": info.get('exchange')
            },
            "holdings": holdings,
            "averages": {"pe": 28.4, "eps": 4.2, "div": 1.5, "risk": 1.1, "exp": 0.45, "mkt": 150000000000},
            "performance": perf,
            "peers": [], 
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', '')},
            "news": stock.news[:3] if stock.news else []
        })
    except Exception as e:
        logger.error(f"Error in analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        lows, highs = hist['Low'].min(), hist['High'].max()
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": lows * 0.99, "high": lows * 1.01}, "resistance": {"low": highs * 0.99, "high": highs * 1.01}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
        })
    except Exception as e:
        logger.error(f"Error in history: {e}")
        return {"data": []}

@app.get("/api/forecast/{ticker}")
@app.get("/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        return json_compatible(engine.run_forecast())
    except Exception as e:
        logger.error(f"Error in forecast: {e}")
        return {}

# Serve Frontend Static Files
import os
frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent intercepting API calls
        if full_path.startswith("api/") or full_path.startswith("health") or full_path == "":
            # Fall through to FastAPI routes if it's an API or empty root
            # (FastAPI matches routes in order, but catch-all needs logic)
            pass
        
        # Check if the requested file exists in dist
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Default to index.html for SPA
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "API is running, but frontend was not built."}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
