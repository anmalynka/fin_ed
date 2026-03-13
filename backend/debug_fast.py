import yfinance as yf

def debug_fast_info(symbol):
    print(f"\n--- Fast Info for {symbol} ---")
    ticker = yf.Ticker(symbol)
    fast = ticker.fast_info
    for attr in dir(fast):
        if not attr.startswith('_'):
            try:
                print(f"{attr}: {getattr(fast, attr)}")
            except:
                pass

if __name__ == "__main__":
    debug_fast_info("SCHG")
