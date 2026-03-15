import yfinance as yf
import requests

def test_ticker(symbol):
    print(f"--- Testing {symbol} ---")
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})
    
    ticker = yf.Ticker(symbol, session=session)
    
    print("\n[INFO KEYS]:")
    try:
        info = ticker.info
        print(list(info.keys())[:20])
        print(f"currentPrice: {info.get('currentPrice')}")
        print(f"regularMarketPrice: {info.get('regularMarketPrice')}")
    except Exception as e:
        print(f"Info Error: {e}")

    print("\n[FAST INFO]:")
    try:
        fast = ticker.fast_info
        print(f"last_price: {getattr(fast, 'last_price', 'MISSING')}")
        print(f"market_cap: {getattr(fast, 'market_cap', 'MISSING')}")
    except Exception as e:
        print(f"Fast Info Error: {e}")

    print("\n[HISTORY]:")
    try:
        hist = ticker.history(period="1d")
        print(hist)
    except Exception as e:
        print(f"History Error: {e}")

if __name__ == "__main__":
    test_ticker("AAPL")
