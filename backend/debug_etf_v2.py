import yfinance as yf
import json

def debug_etf_expensive(symbol):
    print(f"\n--- Debugging {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    # Print all keys that might contain expense info
    found = {}
    for k, v in info.items():
        lk = k.lower()
        if 'exp' in lk or 'fee' in lk or 'ratio' in lk:
            found[k] = v
            
    print(json.dumps(found, indent=2))

if __name__ == "__main__":
    debug_etf_expensive("SCHD")
    debug_etf_expensive("SCHG")
    debug_etf_expensive("VOO")
