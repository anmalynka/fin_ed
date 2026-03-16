import yfinance as yf
import json
from services.valuation import ValuationService

def debug_goog():
    ticker = yf.Ticker("GOOG")
    info = ticker.info
    print(f"Ticker: GOOG")
    print(f"Current Price: {info.get('currentPrice')}")
    print(f"Earnings Growth: {info.get('earningsGrowth')}")
    print(f"Total Cash: {info.get('totalCash')}")
    print(f"Total Debt: {info.get('totalDebt')}")
    print(f"Shares Outstanding: {info.get('sharesOutstanding')}")
    
    cf = ticker.cash_flow
    if not cf.empty:
        print("Cash Flow Index:")
        print(cf.index.tolist())
        if 'Free Cash Flow' in cf.index:
            print(f"Latest FCF: {cf.loc['Free Cash Flow'].iloc[0]}")
    
    val = ValuationService("GOOG")
    res = val.run_dcf_model()
    print("\nDCF Result:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    debug_goog()
