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

    def run_dcf_model(self):
        try:
            # 1. Gather Data
            current_p = self.info.get('currentPrice') or self.fast_info.last_price or 0
            eps = self.info.get('trailingEps') or self.info.get('forwardEps') or 0.0
            shares = self.info.get('sharesOutstanding') or self.info.get('impliedSharesOutstanding') or 1
            
            # --- CURRENCY ALIGNMENT FIX ---
            net_income_raw = self.info.get('netIncomeToCommon', 0)
            conversion_factor = 1.0
            if net_income_raw > 0 and eps > 0:
                implied_eps_local = net_income_raw / shares
                if abs(eps / implied_eps_local - 1) > 0.1:
                    conversion_factor = eps / implied_eps_local
                    logger.info(f"Currency mismatch detected for {self.ticker_symbol}. Conversion factor: {conversion_factor:.4f}")

            fcf = (self.info.get('freeCashflow') or (net_income_raw * 0.8)) * conversion_factor
            total_cash = self.info.get('totalCash', 0) * conversion_factor
            total_debt = self.info.get('totalDebt', 0) * conversion_factor

            growth = self.info.get('earningsGrowth') or self.info.get('revenueGrowth') or 0.10
            beta = self.info.get('beta', 1.0)
            
            if growth > 1: growth /= 100
            growth = max(0.05, min(0.25, growth))

            sector = self.info.get('sector', 'Unknown')
            sector_map = {
                "Technology": 25.0, "Communication Services": 22.0, "Financial Services": 12.0,
                "Healthcare": 22.0, "Energy": 10.0, "Consumer Defensive": 20.0,
                "Utilities": 18.0, "Real Estate": 15.0, "Industrials": 17.0, "Basic Materials": 12.0
            }
            pe_sector = sector_map.get(sector, 18.0)

            # 1. Relative Valuation (0.40)
            val_relative = eps * pe_sector

            # 2. DCF (0.20) -> 10-Year FCF Forecast + Terminal Value
            r = 0.04 + (beta * 0.05)
            r = max(0.07, r)
            gp = 0.02 
            
            pv_fcf = 0
            fcf_n = fcf
            for i in range(1, 11):
                fade_multiplier = (1 - (i / 10) * 0.3)
                fcf_n *= (1 + (growth * fade_multiplier))
                pv_fcf += fcf_n / (1 + r) ** i
            
            tv = (fcf_n * (1 + gp)) / (r - gp)
            pv_tv = tv / (1 + r) ** 10
            
            enterprise_val = pv_fcf + pv_tv
            net_cash = total_cash - total_debt
            equity_val = enterprise_val + net_cash
            val_dcf = equity_val / shares if shares > 0 else 0
            if val_dcf < 0: val_dcf *= -1

            # 3. PEG (0.40)
            peg_target = 1.25
            val_peg = eps * peg_target * (growth * 100)

            # FINAL BLEND: 40/20/40
            intrinsic_price = (val_relative * 0.40) + (val_dcf * 0.20) + (val_peg * 0.40)
            if intrinsic_price < 0: intrinsic_price *= -1

            calc_summary = f"Relative: ${val_relative:.1f} | DCF: ${val_dcf:.1f} | PEG: ${val_peg:.1f}"

            return clean_data({
                "intrinsic_price": intrinsic_price,
                "current_price": current_p,
                "status": "UNDERVALUED" if intrinsic_price > current_p else "OVERVALUED",
                "calculation": calc_summary,
                "is_undervalued": intrinsic_price > current_p,
                "industry_pe": pe_sector
            })
        except Exception as e:
            logger.error(f"Error in Blended model: {e}")
            return {"error": str(e), "status": "NEUTRAL", "intrinsic_price": 0}

    def get_performance_history(self):
        try:
            hist = self.ticker.history(period="5y")
            if hist.empty:
                return {"1M": 0, "YTD": 0, "1Y": 0, "3Y": 0, "5Y": 0}

            def calc_return(df, days):
                if len(df) < 2: return 0.0
                start_val = df['Close'].iloc[-min(days, len(df))]
                end_val = df['Close'].iloc[-1]
                return round(((end_val - start_val) / start_val) * 100, 2)

            try:
                ytd_start = pd.Timestamp(datetime.now().year, 1, 1).tz_localize(hist.index.tz)
                ytd_df = hist[hist.index >= ytd_start]
                ytd_return = 0.0
                if not ytd_df.empty:
                    ytd_return = round(((ytd_df['Close'].iloc[-1] - ytd_df['Close'].iloc[0]) / ytd_df['Close'].iloc[0]) * 100, 2)
            except:
                ytd_return = 0.0

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
