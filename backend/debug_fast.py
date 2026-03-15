import os
import sys
import json
import yfinance as yf
import numpy as np
import pandas as pd

# Add backend to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from services.valuation import ValuationService

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

def simulate_analyze(ticker):
    ticker = ticker.upper().strip()
    stock = yf.Ticker(ticker)
    fast = stock.fast_info
    info = stock.info or {}
    
    current_p = safe_float(getattr(fast, 'last_price', None)) or safe_float(info.get('currentPrice'))
    
    if current_p is None:
        hist = stock.history(period="1d")
        if not hist.empty:
            current_p = safe_float(hist['Close'].iloc[-1])

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
    
    response_data = {
        "ticker": ticker,
        "type": info.get('quoteType', 'EQUITY'),
        "industry": info.get('industry') or info.get('sector') or ("Fund" if is_etf else "Finance"),
        "metrics": {
            "price": current_p, 
            "intrinsic": intrinsic, 
            "status": status,
            "eps": safe_float(info.get('trailingEps')) or 0.0, 
            "pe": safe_float(info.get('trailingPE')) or 20.0, 
            "mkt_cap": safe_float(getattr(fast, 'market_cap', None)) or safe_float(info.get('marketCap')),
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
        "news": [] # stock.news sometimes fails or is slow
    }
    
    return json_compatible(response_data)

if __name__ == "__main__":
    res = simulate_analyze("AAPL")
    print(json.dumps(res, indent=2))
