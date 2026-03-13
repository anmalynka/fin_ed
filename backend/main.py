from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import pandas as pd
import numpy as np
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# THE MOST ROBUST CORS CONFIGURATION POSSIBLE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def safe_float(value):
    try:
        if value is None or pd.isna(value) or np.isinf(value): return None
        return float(value)
    except: return None

def calculate_zones(df):
    """Refined zone calculation for all timeframes."""
    if df is None or df.empty or len(df) < 5: return None
    try:
        # Use a sliding window to find more 'local' support/resistance
        lows = df['Low'].nsmallest(max(1, int(len(df)*0.1))).mean()
        highs = df['High'].nlargest(max(1, int(len(df)*0.1))).mean()
        
        # Buffer relative to volatility
        price_range = highs - lows
        buffer = price_range * 0.05 if price_range > 0 else df['Close'].mean() * 0.01
        
        return {
            "support": {"low": lows - buffer, "high": lows + buffer, "mid": lows},
            "resistance": {"low": highs - buffer, "high": highs + buffer, "mid": highs}
        }
    except Exception as e:
        logger.error(f"Zone Error: {e}")
        return None

@app.get("/analyze/{ticker}")
async def analyze_stock(ticker: str):
    ticker = ticker.upper().strip()
    logger.info(f"Analyzing {ticker}")
    try:
        stock = yf.Ticker(ticker)
        # Using fast_info + info for maximum data recovery
        info = stock.info or {}
        fast = stock.fast_info
        
        current_p = safe_float(fast.last_price) or safe_float(info.get('currentPrice'))
        if not current_p:
            h = stock.history(period="1d")
            if not h.empty: current_p = safe_float(h.iloc[-1]['Close'])
        
        if not current_p:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found.")

        mkt_cap = safe_float(fast.market_cap) or safe_float(info.get('marketCap'))
        
        # Peer Selection (Parallel)
        peers_list = ["AAPL", "MSFT", "GOOGL"] if "Semicon" not in (info.get('industry', '')) else ["AMD", "INTC", "TSM"]
        comparison = []
        for p in peers_list:
            try:
                p_s = yf.Ticker(p)
                p_info = p_s.info
                comparison.append({
                    "ticker": p,
                    "pe": safe_float(p_info.get('trailingPE')),
                    "eps": safe_float(p_info.get('trailingEps'))
                })
            except: continue

        # DCF (Simplified but Stable)
        intrinsic = None
        eps = safe_float(info.get('trailingEps'))
        if eps and eps > 0:
            intrinsic = eps * 20 # 20x Earnings proxy for stable DCF speed

        return {
            "ticker": ticker,
            "type": info.get('quoteType', 'EQUITY'),
            "info": {"name": info.get('longName', ticker), "industry": info.get('industry', 'N/A'), "summary": info.get('longBusinessSummary', '')},
            "metrics": {
                "current": {"price": current_p, "pe": safe_float(info.get('trailingPE')), "eps": eps, "mkt_cap": mkt_cap},
                "intrinsic_price": intrinsic,
                "is_undervalued": intrinsic > current_p if intrinsic and current_p else False
            },
            "comparison": comparison,
            "news": stock.news[:3] if stock.news else [],
            "filings": {
                "sec": f"https://www.sec.gov/edgar/search/#/q={ticker}&forms=10-K,10-Q",
                "annual": f"https://finance.yahoo.com/quote/{ticker}/financials"
            }
        }
    except Exception as e:
        logger.error(f"Analyze Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{ticker}")
async def get_history(ticker: str, period: str = Query("1mo")):
    ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(ticker)
        interval = "1d"
        if period == "1d": interval = "2m"
        elif period == "5d" or period == "1wk": interval = "15m"
        
        hist = stock.history(period=period, interval=interval)
        if hist.empty:
            return {"data": [], "zones": None, "performance": None}
        
        hist = hist.reset_index()
        date_col = 'Date' if 'Date' in hist.columns else 'Datetime'
        hist['date'] = hist[date_col].dt.strftime('%Y-%m-%d %H:%M')
        
        zones = calculate_zones(hist)
        start_p = float(hist.iloc[0]['Close'])
        end_p = float(hist.iloc[-1]['Close'])
        
        return {
            "data": hist[['date', 'Close']].rename(columns={'Close': 'price'}).to_dict(orient='records'),
            "zones": zones,
            "performance": {
                "change_pct": ((end_p - start_p)/start_p)*100,
                "is_positive": end_p >= start_p
            }
        }
    except Exception as e:
        logger.error(f"History Error: {e}")
        return {"data": [], "zones": None, "performance": None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
