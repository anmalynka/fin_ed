from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import asyncio
from datetime import datetime, timedelta

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

async def fetch_peer_full_history(ticker):
    try:
        loop = asyncio.get_event_loop()
        s = yf.Ticker(ticker)
        info = await loop.run_in_executor(None, lambda: s.info)
        hist = await loop.run_in_executor(None, lambda: s.history(period="2y"))
        
        current_p = safe_float(info.get('currentPrice'))
        p_1y_ago = safe_float(hist.iloc[-252]['Close']) if len(hist) > 252 else current_p
        
        # Financials for 1Y ago EPS
        fin = await loop.run_in_executor(None, lambda: s.financials)
        eps_now = safe_float(info.get('trailingEps'))
        
        # Robust historical EPS extraction
        eps_1y = eps_now
        if not fin.empty:
            possible_rows = ['Basic EPS', 'Diluted EPS', 'Net Income']
            for row in possible_rows:
                if row in fin.index and fin.shape[1] > 1:
                    eps_1y = safe_float(fin.loc[row].iloc[1])
                    if eps_1y is not None: break

        return {
            "ticker": ticker,
            "pe_now": safe_float(info.get('trailingPE')),
            "pe_1y": safe_float(p_1y_ago / eps_1y) if eps_1y and eps_1y > 0 else safe_float(info.get('trailingPE')),
            "eps_now": eps_now,
            "eps_1y": eps_1y,
            "div_price_now": safe_float((info.get('dividendRate', 0) / current_p) * 100) if current_p else 0,
            "div_price_1y": safe_float((info.get('dividendRate', 0) / p_1y_ago) * 100) if p_1y_ago else 0
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
        
        # 1. Fair Value Logic (User Formula: EPS * Growth)
        eps = safe_float(info.get('trailingEps'))
        growth = info.get('earningsGrowth') or 0.15
        intrinsic = abs(eps * (growth * 100)) if eps else 0 # Ensure positive
        
        current_p = safe_float(fast.last_price) or safe_float(info.get('currentPrice'))
        
        status = "NEUTRAL"
        if intrinsic and current_p:
            # If value lower than price - Buy
            if intrinsic < current_p * 0.95: status = "UNDERVALUED"
            # If value higher than price - Point of too high
            elif intrinsic > current_p * 1.05: status = "OVERVALUED"
            else: status = "NEUTRAL"

        # 2. Peers
        peer_tickers = ["AAPL", "MSFT", "GOOGL"]
        if "Semicon" in industry: peer_tickers = ["AMD", "INTC", "TSM"]
        elif "Auto" in industry: peer_tickers = ["F", "GM", "TM"]
        
        tasks = [fetch_peer_full_history(p) for p in peer_tickers if p != ticker]
        peers_data = await asyncio.gather(*tasks)

        perf = {}
        for p in ["1mo", "ytd", "1y"]:
            h = stock.history(period=p)
            if not h.empty:
                s, e = h.iloc[0]['Close'], h.iloc[-1]['Close']
                perf[p.upper()] = round(((e - s)/s)*100, 2)

        return json_compatible({
            "ticker": ticker,
            "metrics": {
                "price": current_p, "intrinsic": intrinsic, "status": status,
                "eps": eps, "pe": safe_float(info.get('trailingPE')),
                "mkt_cap": safe_float(info.get('marketCap')),
                "div_annual": safe_float(info.get('dividendRate')),
                "beta": safe_float(info.get('beta')),
                "exchange": info.get('exchange')
            },
            "peers": [p for p in peers_data if p],
            "performance": perf,
            "info": {"name": info.get('longName', ticker), "summary": info.get('longBusinessSummary', '')},
            "news": stock.news[:3] if stock.news else []
        })
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Fetch error.")

@app.get("/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1wk")):
    try:
        stock = yf.Ticker(ticker.upper())
        interval = "1d"
        # 24h/Hourly for 1D trend
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
    except: return {"data": []}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
