import yfinance as yf
import json

def debug_etf(symbol):
    print(f"--- Debugging {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    # Common keys for expense ratio
    keys_to_check = [
        'expenseRatio', 
        'annualReportExpenseRatio', 
        'totalExpenseRatio', 
        'feesExpensesMax',
        'netExpRatio',
        'yield'
    ]
    
    found = {}
    for k in keys_to_check:
        found[k] = info.get(k)
        
    print(json.dumps(found, indent=2))
    
    # Print all keys that look like 'exp' or 'ratio'
    print("\nMatching keys in info:")
    for k in info.keys():
        if 'exp' in k.lower() or 'ratio' in k.lower() or 'fee' in k.lower():
            print(f"{k}: {info[k]}")

if __name__ == "__main__":
    debug_etf("SCHD")
    debug_etf("VOO")
