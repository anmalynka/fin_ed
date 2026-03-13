import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class ForecastEngine:
    def __init__(self, ticker):
        self.ticker = ticker

    def run_forecast(self):
        stock = yf.Ticker(self.ticker)
        # Use 2 years for stable drift calculation
        df = stock.history(period="2y")
        if len(df) < 100: return None
        
        prices = df['Close'].values
        dates = df.index
        
        # 1. Calculate Historical Log Returns
        log_returns = np.log(prices[1:] / prices[:-1])
        mu = log_returns.mean()
        sigma = log_returns.std()
        last_price = prices[-1]
        
        # 2. Stochastic Projection (Geometric Brownian Motion)
        # This creates the realistic "jagged" paths you liked
        days = 252
        dt = 1
        
        # Add Mean Reversion to keep the long-term trend grounded
        mean_price = prices.mean()
        reversion_speed = 0.02
        
        forecast_path = [last_price]
        for i in range(days):
            epsilon = np.random.normal()
            # Drift component (Historical growth)
            drift = (mu - 0.5 * sigma**2) * dt
            # Volatility component (Ticker-specific noise)
            diffusion = sigma * epsilon * np.sqrt(dt)
            # Reversion component (Pull back to average)
            reversion = reversion_speed * (np.log(mean_price) - np.log(forecast_path[-1]))
            
            next_price = forecast_path[-1] * np.exp(drift + diffusion + reversion)
            forecast_path.append(next_price)
            
        # 3. Create Continuous Timeline
        last_date = dates[-1]
        forecast_dates = [(last_date + timedelta(days=i+1)) for i in range(days)]
        
        # 4. Linear Baseline for comparison
        baseline = [last_price * np.exp(mu * (i+1)) for i in range(days)]

        # Prepare for UI
        # History (Last 100 days)
        history_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(dates[-100:], prices[-100:])]
        # Forecast (Next 252 days)
        forecast_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(forecast_dates, forecast_path[1:])]
        # Baseline
        baseline_points = [{"date": d.strftime('%Y-%m-%d'), "price": round(float(p), 2)} for d, p in zip(forecast_dates, baseline)]

        return {
            "history": history_points,
            "hybrid": forecast_points,
            "baseline": baseline_points
        }
