import yfinance as yf
import json

def debug_pe_metrics(symbol):
    print(f"\n--- Searching P/E Metrics for {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    
    # Common keys for P/E averages and industry metrics
    keys_to_check = [
        'trailingPE', 'forwardPE', 'priceToSalesTrailing12Months',
        'fiveYearAvgPE', 'sectorPE', 'industryPE', 'peRatio',
        'fiveYearAvgDividendYield' # checking if other 5yr metrics exist
    ]
    
    # Also search for any key containing 'PE' or 'average'
    found_keys = {}
    for k, v in info.items():
        if 'PE' in k or 'average' in k.lower() or 'median' in k.lower():
            found_keys[k] = v
            
    print("Filtered Info Keys:")
    print(json.dumps(found_keys, indent=2))

if __name__ == "__main__":
    debug_pe_metrics("AAPL")
    debug_pe_metrics("MSFT")
    debug_pe_metrics("SPY")
