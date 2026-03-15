import os
import sys

# CRITICAL: This must be the very first thing in the file
# It adds the 'backend' directory to the search path so 'import services' works
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
import requests
from services.forecaster import ForecastEngine
from services.financials import FinancialsService
from services.valuation import ValuationService
from services.technical_analysis import TechnicalAnalysisService

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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response

@app.get("/api/health")
@app.get("/health")
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
    logger.info(f"Analyzing ticker: {ticker}")
    try:
        # Initialize services
        stock = yf.Ticker(ticker)
        val_service = ValuationService(ticker)
        fin_service = FinancialsService(ticker)
        tech_service = TechnicalAnalysisService(ticker)
        
        info = stock.info or {}
        fast = stock.fast_info
        
        # Fallback for missing info (common on Render/Scraping blocks)
        current_p = safe_float(fast.last_price) or safe_float(info.get('currentPrice')) or safe_float(info.get('regularMarketPrice'))
        
        # If we still don't have a price, try history
        if current_p is None:
            h = stock.history(period="1d")
            if not h.empty:
                current_p = safe_float(h['Close'].iloc[-1])

        if current_p is None:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found or no price data available.")

        quote_type = info.get('quoteType', 'EQUITY')
        is_etf = quote_type == 'ETF'
        
        # 1. ETF Specific Data
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

        # 2. Metrics & Expense Ratio
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
        
        if (not div_rate or div_rate == 0) and div_yield > 0 and current_p: 
            div_rate = (div_yield / 100) * current_p

        # 3. Decision Logic using DCF and PE
        eps = safe_float(info.get('trailingEps'))
        if not eps:
            # Try to calculate EPS from financials
            try:
                income = stock.financials
                if not income.empty and 'Net Income' in income.index:
                    net_income = income.loc['Net Income'].iloc[0]
                    shares = fast.shares or info.get('sharesOutstanding')
                    if shares:
                        eps = net_income / shares
            except: pass

        dcf_val = val_service.run_dcf_model()
        intrinsic = safe_float(dcf_val.get('intrinsic_price')) or current_p
        
        # Status logic
        status = "NEUTRAL"
        if intrinsic > current_p * 1.15: status = "UNDERVALUED"
        elif intrinsic < current_p * 0.85: status = "OVERVALUED"

        # 4. Performance
        perf = {}
        for p in [("1M", "1mo"), ("YTD", "ytd"), ("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y")]:
            h = stock.history(period=p[1])
            if not h.empty:
                s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                perf[p[0]] = round(((e - s)/s)*100, 2)

        # 5. Industry Averages (Smart Fallback)
        industry = info.get('industry', 'Exchange Traded Fund' if is_etf else 'Technology')
        sector = info.get('sector', 'N/A')
        
        # Dynamic averages based on sector if possible
        avg_pe = 25.0
        if sector == 'Technology': avg_pe = 35.0
        elif sector == 'Financial Services': avg_pe = 15.0
        elif sector == 'Healthcare': avg_pe = 22.0
        
        # 6. Peers
        peers = []
        # In a real app, we'd fetch actual peers. Here we can use some top stocks if technology
        if sector == 'Technology' and ticker != 'AAPL': peers.append({"ticker": "AAPL", "pe_now": 30.5, "eps_now": 6.5, "div_price_now": 0.5})
        if sector == 'Technology' and ticker != 'MSFT': peers.append({"ticker": "MSFT", "pe_now": 35.2, "eps_now": 11.8, "div_price_now": 0.7})

        return json_compatible({
            "ticker": ticker,
            "type": quote_type,
            "industry": industry,
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
                "eps": eps, "pe": safe_float(info.get('trailingPE')), "mkt_cap": safe_float(fast.market_cap) or safe_float(info.get('marketCap')),
                "div_annual": safe_float(div_rate), "div_yield": safe_float(div_yield),
                "beta": safe_float(info.get('beta')), "expense_ratio": safe_float(exp), "exchange": info.get('exchange')
            },
            "holdings": holdings,
            "averages": {"pe": avg_pe, "eps": 4.5, "div": 1.8, "risk": 1.0, "exp": 0.5, "mkt": 200000000000},
            "performance": perf,
            "peers": peers, 
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', 'No company summary available.')},
            "news": stock.news[:3] if stock.news else []
        })
    except Exception as e:
        logger.error(f"Error in analyze: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Data fetch failed: {str(e)}")

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
        result = engine.run_forecast()
        return json_compatible(result) if result else {}
    except Exception as e:
        logger.error(f"Error in forecast: {e}")
        return {}

# SERVE FRONTEND
# Serve Frontend Static Files
frontend_dist = os.path.abspath(os.path.join(current_dir, "..", "frontend", "dist"))

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Prevent intercepting API calls
        if full_path.startswith("api/") or full_path.startswith("health"):
            return None # This won't work as expected in a catch-all, but order matters
        
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse(os.path.join(frontend_dist, "index.html"))

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "API is running, but frontend was not built."}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
