import yfinance as yf
import json

def debug_etf(symbol):
    print(f"--- Debugging {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    # Common keys for dividends
    keys_to_check = [
        'dividendRate', 
        'trailingAnnualDividendRate', 
        'dividendYield', 
        'trailingAnnualDividendYield',
        'yield'
    ]
    
    found = {}
    for k in keys_to_check:
        found[k] = info.get(k)
        
    print(json.dumps(found, indent=2))

if __name__ == "__main__":
    debug_etf("SCHD")
    debug_etf("AAPL")
