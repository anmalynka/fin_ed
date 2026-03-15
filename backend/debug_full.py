import yfinance as yf
import pandas as pd
import json

def investigate(ticker_symbol):
    print(f"\n{'='*20} INVESTIGATING: {ticker_symbol} {'='*20}")
    t = yf.Ticker(ticker_symbol)
    
    # 1. Test .info
    print("[1] Testing .info...")
    try:
        info = t.info
        if not info:
            print("FAILED: .info returned empty dict")
        else:
            print(f"SUCCESS: Found {len(info)} keys in .info")
            # Print a few key values to see if they are valid or decrypted
            important_keys = ['longName', 'currentPrice', 'trailingEps', 'marketCap', 'trailingPE']
            for k in important_keys:
                print(f"  - {k}: {info.get(k)}")
    except Exception as e:
        print(f"ERROR in .info: {e}")

    # 2. Test .fast_info
    print("\n[2] Testing .fast_info...")
    try:
        fast = t.fast_info
        print(f"  - last_price: {getattr(fast, 'last_price', 'N/A')}")
        print(f"  - market_cap: {getattr(fast, 'market_cap', 'N/A')}")
        print(f"  - currency: {getattr(fast, 'currency', 'N/A')}")
    except Exception as e:
        print(f"ERROR in .fast_info: {e}")

    # 3. Test .history
    print("\n[3] Testing .history(period='1d')...")
    try:
        hist = t.history(period="1d")
        if hist.empty:
            print("FAILED: .history returned empty DataFrame")
        else:
            print("SUCCESS: .history returned data")
            print(hist[['Open', 'High', 'Low', 'Close']])
    except Exception as e:
        print(f"ERROR in .history: {e}")

    # 4. Test Financials (for EPS calculation fallback)
    print("\n[4] Testing .financials...")
    try:
        fin = t.financials
        if fin.empty:
            print("FAILED: .financials returned empty DataFrame")
        else:
            print(f"SUCCESS: .financials found with columns: {list(fin.columns)}")
    except Exception as e:
        print(f"ERROR in .financials: {e}")

if __name__ == "__main__":
    for s in ["AAPL", "TSLA", "NONEXISTENT_TICKER"]:
        investigate(s)
