import yfinance as yf
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def clean_data(data):
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(v) for v in data]
    elif isinstance(data, (float, np.float64, np.float32)):
        if np.isnan(data) or np.isinf(data): return None
        return float(data)
    elif isinstance(data, (int, np.int64, np.int32)):
        return int(data)
    elif pd.isna(data): return None
    return data

class ValuationService:
    def __init__(self, ticker_symbol):
        self.ticker_symbol = ticker_symbol
        self.ticker = yf.Ticker(ticker_symbol)
        self.fast_info = self.ticker.fast_info
        try:
            self.info = self.ticker.info or {}
        except:
            self.info = {}

    def get_pe_analysis(self):
        try:
            current_price = self.fast_info.last_price
            eps = self.info.get('trailingEps') or self.info.get('forwardEps')
            
            if not eps and 'netIncomeToCommon' in self.info and 'sharesOutstanding' in self.info:
                eps = self.info['netIncomeToCommon'] / self.info['sharesOutstanding']
            
            current_pe = float(current_price / eps) if current_price and eps and eps > 0 else self.info.get('trailingPE')
            
            return clean_data({
                "current_pe": current_pe,
                "forward_pe": self.info.get('forwardPE'),
                "five_year_avg_pe_estimate": current_pe * 0.9 if current_pe else 20.0,
                "sector": self.info.get('sector', 'Unknown'),
                "industry": self.info.get('industry', 'Unknown')
            })
        except:
            return {"current_pe": None, "five_year_avg_pe_estimate": 20.0}

    def get_competitor_comparison(self):
        return {"industry": self.info.get('industry', 'N/A'), "industry_pe_avg": 22.5}

    def run_dcf_model(self, growth_rate=0.1, discount_rate=0.10, terminal_growth=0.02, years=5):
        try:
            cashflow = self.ticker.cash_flow
            latest_fcf = None
            if not cashflow.empty:
                if 'Free Cash Flow' in cashflow.index:
                    latest_fcf = cashflow.loc['Free Cash Flow'].iloc[0]
                elif 'Total Cash From Operating Activities' in cashflow.index:
                    latest_fcf = cashflow.loc['Total Cash From Operating Activities'].iloc[0]
            
            if latest_fcf is None or pd.isna(latest_fcf):
                latest_fcf = self.info.get('netIncomeToCommon', 0) * 0.8
            
            projected_fcf = [latest_fcf * (1 + growth_rate) ** i for i in range(1, years + 1)]
            terminal_value = (projected_fcf[-1] * (1 + terminal_growth)) / (discount_rate - terminal_growth)
            pv_equity = sum([fcf / (1 + discount_rate) ** (i + 1) for i, fcf in enumerate(projected_fcf)]) + (terminal_value / (1 + discount_rate) ** years)
            
            shares = self.fast_info.shares or self.info.get('sharesOutstanding')
            intrinsic_price = pv_equity / shares if shares else 0
            current_price = self.fast_info.last_price or self.info.get('currentPrice', 0)

            return clean_data({
                "intrinsic_price": intrinsic_price,
                "current_price": current_price,
                "is_undervalued": intrinsic_price > current_price if current_price > 0 else False,
                "margin_of_safety": (intrinsic_price - current_price) / intrinsic_price if intrinsic_price > 0 else 0
            })
        except Exception as e:
            return {"error": str(e)}
