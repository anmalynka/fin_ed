import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalysisService:
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        self.ticker = yf.Ticker(ticker_symbol)

    def get_pivot_points(self, period="1y"):
        """Calculate basic pivot points and support/resistance."""
        try:
            hist = self.ticker.history(period=period)
            if hist.empty:
                logger.warning(f"No history found for {self.ticker_symbol}")
                return {"error": "Could not fetch historical data"}

            # Use the most recent full candle (usually previous day)
            latest = hist.iloc[-2]
            high = latest['High']
            low = latest['Low']
            close = latest['Close']

            pp = (high + low + close) / 3
            r1 = (2 * pp) - low
            s1 = (2 * pp) - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)

            return {
                "pivot_point": float(pp),
                "resistance_1": float(r1),
                "support_1": float(s1),
                "resistance_2": float(r2),
                "support_2": float(s2),
                "current_price": float(hist.iloc[-1]['Close'])
            }
        except Exception as e:
            logger.error(f"Error calculating pivots for {self.ticker_symbol}: {e}")
            return {}

    def get_catalysts(self):
        """Get upcoming earnings and news as potential catalysts."""
        try:
            calendar = self.ticker.calendar
            news = self.ticker.news
            
            # Safely convert calendar to dict
            cal_dict = {}
            if isinstance(calendar, pd.DataFrame):
                cal_dict = calendar.to_dict()
            elif isinstance(calendar, dict):
                cal_dict = calendar
            elif isinstance(calendar, list):
                cal_dict = {"upcoming_events": calendar}
            
            # Ensure news is a list
            safe_news = news if isinstance(news, list) else []

            return {
                "upcoming_earnings": cal_dict,
                "recent_news": safe_news[:5] if safe_news else []
            }
        except Exception as e:
            logger.error(f"Error fetching catalysts for {self.ticker_symbol}: {e}")
            return {"upcoming_earnings": {}, "recent_news": []}
