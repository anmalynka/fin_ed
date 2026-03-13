import yfinance as yf
import json
import pandas as pd

def test_ticker(symbol):
    print(f"\n--- Testing {symbol} ---")
    ticker = yf.Ticker(symbol)
    
    # Test 1: Basic Info
    try:
        info = ticker.info
        print(f"Info keys found: {len(info) if info else 0}")
        print(f"Current Price: {info.get('currentPrice')}")
    except Exception as e:
        print(f"Info Error: {e}")

    # Test 2: History
    try:
        hist = ticker.history(period="1d")
        print(f"History rows: {len(hist)}")
    except Exception as e:
        print(f"History Error: {e}")

    # Test 3: Financials
    try:
        fin = ticker.financials
        print(f"Financials rows: {len(fin)}")
    except Exception as e:
        print(f"Financials Error: {e}")

if __name__ == "__main__":
    test_ticker("AAPL")
    test_ticker("NVDA")
