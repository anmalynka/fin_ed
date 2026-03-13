import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ForecastEngine:
    def __init__(self, ticker):
        self.ticker = ticker

    def run_forecast(self):
        stock = yf.Ticker(self.ticker)
        # Use 2 years to get enough context for a stable trend
        df = stock.history(period="2y")
        if len(df) < 100: return None
        
        prices = df['Close'].values
        dates = df.index
        
        # 1. Historical Stats
        log_returns = np.log(prices[1:] / prices[:-1])
        mu = log_returns.mean()
        sigma = log_returns.std()
        last_price = prices[-1]
        
        # 2. Project 252 trading days (1 Year)
        days = 252
        dt = 1
        mean_price = prices.mean()
        reversion_speed = 0.015 # Slower reversion for a longer trend
        
        forecast_path = []
        current_p = last_price
        for i in range(days):
            epsilon = np.random.normal()
            drift = (mu - 0.5 * sigma**2) * dt
            diffusion = sigma * epsilon * np.sqrt(dt)
            reversion = reversion_speed * (np.log(mean_price) - np.log(current_p))
            
            current_p = current_p * np.exp(drift + diffusion + reversion)
            forecast_path.append(current_p)
            
        # 3. Timeline Generation (Ensuring no skips)
        last_date = dates[-1]
        # We start from the day AFTER the last historical date
        forecast_dates = [(last_date + timedelta(days=i+1)) for i in range(days)]
        
        # Linear Baseline (Perfect Drift)
        baseline = [last_price * np.exp(mu * (i+1)) for i in range(days)]

        # 4. Formulate Result
        # History (Last 100 days)
        history_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(dates[-100:], prices[-100:])]
        
        # Forecast (Next 252 days)
        forecast_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(forecast_dates, forecast_path)]
        
        # Baseline
        baseline_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(forecast_dates, baseline)]

        return {
            "history": history_points,
            "hybrid": forecast_points,
            "baseline": baseline_points
        }
