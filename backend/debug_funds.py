import yfinance as yf

def debug_funds_data(symbol):
    print(f"\n--- Funds Data for {symbol} ---")
    ticker = yf.Ticker(symbol)
    try:
        # Some versions of yfinance have funds_data
        data = ticker.funds_data
        print(f"Description: {data.description}")
        print(f"Fund Overview: {data.fund_overview}")
        print(f"Fund Operations: {data.fund_operations}")
    except Exception as e:
        print(f"Error fetching funds_data: {e}")

if __name__ == "__main__":
    debug_funds_data("SCHG")
    debug_funds_data("SCHD")
