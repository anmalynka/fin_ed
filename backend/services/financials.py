import yfinance as yf
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def clean_data(data):
    """Deeply clean data to ensure it's JSON serializable."""
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(v) for v in data]
    elif isinstance(data, (float, np.float64, np.float32)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, (int, np.int64, np.int32)):
        return int(data)
    elif pd.isna(data):
        return None
    return data

class FinancialsService:
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        self.ticker = yf.Ticker(ticker_symbol)

    def _safe_to_dict(self, data):
        """Helper to safely convert DataFrames or dicts to a serializable format."""
        try:
            if isinstance(data, pd.DataFrame):
                # Convert to dict and clean
                return clean_data(data.to_dict())
            if isinstance(data, dict):
                return clean_data(data)
            return {}
        except Exception as e:
            logger.error(f"Error converting data to dict: {e}")
            return {}

    def get_financial_statements(self):
        """Fetch income statement, balance sheet, and cash flow."""
        try:
            # Explicitly call the methods
            return {
                "income_statement": self._safe_to_dict(self.ticker.financials),
                "balance_sheet": self._safe_to_dict(self.ticker.balance_sheet),
                "cash_flow": self._safe_to_dict(self.ticker.cash_flow)
            }
        except Exception as e:
            logger.error(f"Error fetching financials: {e}")
            return {"income_statement": {}, "balance_sheet": {}, "cash_flow": {}}

    def get_filings_info(self):
        """Get info about SEC filings (URLs)."""
        return {
            "latest_10k": f"https://www.sec.gov/edgar/search/#/q={self.ticker_symbol}&forms=10-K",
            "annual_report": f"https://finance.yahoo.com/quote/{self.ticker_symbol}/financials"
        }

    def get_earnings_summary(self):
        """Get basic earnings info."""
        try:
            return {
                "earnings": self._safe_to_dict(getattr(self.ticker, 'earnings', {})),
                "calendar": self._safe_to_dict(getattr(self.ticker, 'calendar', {}))
            }
        except Exception as e:
            return {"earnings": {}, "calendar": {}}
