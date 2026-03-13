from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import asyncio
from datetime import datetime, timedelta
from services.forecaster import ForecastEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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

def get_industry_averages(industry):
    base = {"pe": 24.0, "eps": 4.0, "div": 1.5, "risk": 1.0, "exp": 0.5, "mkt": 50000000000}
    averages = {
        "Semiconductors": {"pe": 35.2, "div": 1.1, "risk": 1.45, "exp": 0.0, "mkt": 150000000000},
        "Software—Infrastructure": {"pe": 42.5, "div": 0.8, "risk": 1.2, "exp": 0.0, "mkt": 200000000000},
        "Auto Manufacturers": {"pe": 12.4, "div": 2.1, "risk": 1.6, "exp": 0.0, "mkt": 80000000000},
        "Oil & Gas Integrated": {"pe": 8.5, "div": 4.2, "risk": 0.9, "exp": 0.0, "mkt": 120000000000},
        "Consumer Electronics": {"pe": 29.4, "div": 0.6, "risk": 1.2, "exp": 0.0, "mkt": 180000000000}
    }
    res = averages.get(industry, base)
    for k, v in base.items():
        if k not in res: res[k] = v
    return res

async def fetch_peer_historical(ticker):
    try:
        loop = asyncio.get_event_loop()
        s = yf.Ticker(ticker)
        info = await loop.run_in_executor(None, lambda: s.info)
        hist = await loop.run_in_executor(None, lambda: s.history(period="2y"))
        
        curr_p = safe_float(info.get('currentPrice'))
        p_1y = safe_float(hist.iloc[-252]['Close']) if len(hist) > 252 else curr_p
        eps_now = safe_float(info.get('trailingEps'))
        
        return {
            "ticker": ticker,
            "pe_now": safe_float(info.get('trailingPE')),
            "pe_1y": safe_float(p_1y / eps_now) if eps_now and eps_now > 0 else 20.0,
            "eps_now": eps_now,
            "eps_1y": eps_now * 0.9,
            "div_price_now": safe_float((info.get('dividendRate', 0) / curr_p)*100) if curr_p else 0,
            "div_price_1y": 1.5
        }
    except: return None

@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        fast = stock.fast_info
        industry = info.get('industry', 'N/A')
        
        # 1. Decision & Fair Value
        eps = safe_float(info.get('trailingEps'))
        growth = info.get('earningsGrowth') or 0.15
        intrinsic = abs(eps * (growth * 100)) if eps else 0
        current_p = safe_float(fast.last_price) or safe_float(info.get('currentPrice'))
        
        status = "NEUTRAL"
        if intrinsic and current_p:
            if intrinsic > current_p * 1.05: status = "UNDERVALUED"
            elif intrinsic < current_p * 0.95: status = "OVERVALUED"

        # 2. Dynamic Peers
        peer_list = ["AAPL", "MSFT", "GOOGL"]
        if "Oil" in industry: peer_list = ["XOM", "CVX", "SHEL"]
        elif "Semicon" in industry: peer_list = ["AMD", "INTC", "TSM"]
        tasks = [fetch_peer_historical(p) for p in peer_list if p != ticker]
        peers_data = await asyncio.gather(*tasks)

        # 3. Multi-period Performance
        perf = {}
        for p in [("1M", "1mo"), ("YTD", "ytd"), ("1Y", "1y"), ("3Y", "3y"), ("5Y", "5y")]:
            h = stock.history(period=p[1])
            if not h.empty:
                s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                perf[p[0]] = round(((e - s)/s)*100, 2)

        return json_compatible({
            "ticker": ticker, "type": info.get('quoteType', 'EQUITY'), "industry": industry,
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
                "eps": eps, "pe": safe_float(info.get('trailingPE')), "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(info.get('dividendRate')), "beta": safe_float(info.get('beta')),
                "expense_ratio": safe_float(info.get('expenseRatio', 0) * 100), "exchange": info.get('exchange')
            },
            "averages": get_industry_averages(industry),
            "peers": [p for p in peers_data if p],
            "performance": perf,
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', '')},
            "news": stock.news[:3] if stock.news else []
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Data fetch failed.")

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
        
        # Support/Resistance zones for ALL timeframes
        lows = hist['Low'].nsmallest(max(1, int(len(hist)*0.1))).mean()
        highs = hist['High'].nlargest(max(1, int(len(hist)*0.1))).mean()
        buf = (highs - lows) * 0.05 if (highs - lows) > 0 else hist['Close'].mean() * 0.01
        
        start_p, end_p = hist.iloc[0]['Close'], hist.iloc[-1]['Close']
        return json_compatible({
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": {"support": {"low": lows - buf, "high": lows + buf}, "resistance": {"low": highs - buf, "high": highs + buf}},
            "performance": {"is_positive": end_p >= start_p, "pct": round(((end_p - start_p)/start_p)*100, 2)}
        })
    except: return {"data": []}

@app.get("/forecast/{ticker}")
async def get_forecast(ticker: str):
    try:
        engine = ForecastEngine(ticker.upper())
        return json_compatible(engine.run_forecast())
    except: raise HTTPException(status_code=500, detail="Forecast failed.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
