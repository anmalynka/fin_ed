import yfinance as yf
import pandas as pd
import numpy as np

def test_ticker_robustly(symbol):
    print(f"\n--- Testing {symbol} ---")
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        print(f"Info keys: {len(info)}")
        
        # Test Price
        fast = stock.fast_info
        print(f"Fast Price: {fast.last_price}")
        
        # Test History
        hist = stock.history(period="1y")
        print(f"History rows: {len(hist)}")
        
        # Test Cash Flow (often fails for ETFs)
        cf = stock.cash_flow
        print(f"Cash Flow empty: {cf.empty}")
        
        # Test Financials (often fails for ETFs)
        fin = stock.financials
        print(f"Financials empty: {fin.empty}")
        
    except Exception as e:
        print(f"CRITICAL ERROR for {symbol}: {e}")

if __name__ == "__main__":
    test_ticker_robustly("NVDA")
    test_ticker_robustly("SPY") # Common ETF
