import yfinance as yf
import json

def debug_full_info(symbol):
    print(f"\n--- Full Info for {symbol} ---")
    ticker = yf.Ticker(symbol)
    info = ticker.info
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    debug_full_info("SCHG")
