import yfinance as yf
import pandas as pd
import numpy as np
import logging
from datetime import datetime

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

    def run_dcf_model(self, growth_rate=None, discount_rate=None, terminal_growth=0.02, years=10):
        try:
            # 1. Gather Raw Data
            fcf = self.info.get('freeCashflow')
            if fcf is None or pd.isna(fcf):
                # Fallback to operating cash flow - capex or net income proxy
                fcf = self.info.get('netIncomeToCommon', 0) * 0.8
            
            if fcf < 0: fcf *= -1

            cash = self.info.get('totalCash', 0)
            debt = self.info.get('totalDebt', 0)
            minority_interest = self.info.get('minorityInterest', 0)
            shares = self.info.get('sharesOutstanding') or self.info.get('impliedSharesOutstanding')
            mkt_cap = self.info.get('marketCap') or (self.info.get('currentPrice', 0) * (shares or 0))

            # 2. Calculate WACC (Discount Rate)
            beta = self.info.get('beta', 1.0)
            rf = 0.042  # 4.2% Risk-Free Rate
            erp = 0.05  # 5% Equity Risk Premium
            cost_of_equity = rf + (beta * erp)
            
            # Cost of Debt (Estimated pre-tax 6% adjusted for 21% tax rate)
            tax_rate = 0.21
            cost_of_debt_pre_tax = 0.06 
            cost_of_debt_post_tax = cost_of_debt_pre_tax * (1 - tax_rate)
            
            # Weighting
            total_value = mkt_cap + debt
            if total_value > 0:
                w_equity = mkt_cap / total_value
                w_debt = debt / total_value
                wacc = (w_equity * cost_of_equity) + (w_debt * cost_of_debt_post_tax)
            else:
                wacc = 0.09 # Default 9%

            # 3. Growth Rates
            g_stage1 = self.info.get('earningsGrowth') or 0.12
            g_stage1 = max(0.05, min(0.25, g_stage1)) # Sanity cap
            g_terminal = 0.02 # 2% Perpetual Growth

            # 4. Projections
            pv_all_stages = 0
            current_fcf = fcf
            
            # Stage 1: Years 1-5 (High Growth)
            for i in range(1, 6):
                current_fcf *= (1 + g_stage1)
                pv_all_stages += current_fcf / (1 + wacc) ** i
            
            # Stage 2: Years 6-10 (Transition/Fade)
            # Linearly fade from g_stage1 to g_terminal
            for i in range(6, 11):
                fade_step = (i - 5) / 5 # 0.2, 0.4, 0.6, 0.8, 1.0
                current_g = g_stage1 - (fade_step * (g_stage1 - g_terminal))
                current_fcf *= (1 + current_g)
                pv_all_stages += current_fcf / (1 + wacc) ** i
            
            # Stage 3: Terminal Value
            terminal_fcf = current_fcf * (1 + g_terminal)
            tv = terminal_fcf / (wacc - g_terminal) if (wacc - g_terminal) > 0 else terminal_fcf / 0.02
            pv_tv = tv / (1 + wacc) ** 10
            
            # 5. Final Calculation
            enterprise_value = pv_all_stages + pv_tv
            equity_value = enterprise_value + cash - debt - minority_interest
            
            if equity_value < 0: equity_value *= -1
            
            intrinsic_price = equity_value / shares if shares and shares > 0 else 0
            current_price = self.info.get('currentPrice') or self.fast_info.last_price or 0

            return clean_data({
                "intrinsic_price": intrinsic_price,
                "current_price": current_price,
                "status": "UNDERVALUED" if intrinsic_price > current_price else "OVERVALUED",
                "is_undervalued": intrinsic_price > current_price,
                "calculation": f"WACC: {wacc*100:.1f}% | Stage 1 Growth: {g_stage1*100:.1f}%"
            })
        except Exception as e:
            logger.error(f"Error in 3-Stage DCF model: {e}")
            return {"error": str(e), "status": "NEUTRAL", "intrinsic_price": 0}

    def get_performance_history(self):
        """Fetch 5 years of historical data and calculate returns."""
        try:
            hist = self.ticker.history(period="5y")
            if hist.empty:
                return {"1M": 0, "YTD": 0, "1Y": 0, "3Y": 0, "5Y": 0}

            def calc_return(df, days):
                if len(df) < 2: return 0.0
                start_val = df['Close'].iloc[-min(days, len(df))]
                end_val = df['Close'].iloc[-1]
                return round(((end_val - start_val) / start_val) * 100, 2)

            # YTD calculation
            ytd_start = pd.Timestamp(datetime.now().year, 1, 1).tz_localize(hist.index.tz)
            ytd_df = hist[hist.index >= ytd_start]
            ytd_return = 0.0
            if not ytd_df.empty:
                ytd_return = round(((ytd_df['Close'].iloc[-1] - ytd_df['Close'].iloc[0]) / ytd_df['Close'].iloc[0]) * 100, 2)

            return {
                "1M": calc_return(hist, 21),
                "YTD": ytd_return,
                "1Y": calc_return(hist, 252),
                "3Y": calc_return(hist, 756),
                "5Y": calc_return(hist, len(hist))
            }
        except Exception as e:
            logger.error(f"Error calculating performance history: {e}")
            return {"1M": 0, "YTD": 0, "1Y": 0, "3Y": 0, "5Y": 0}
